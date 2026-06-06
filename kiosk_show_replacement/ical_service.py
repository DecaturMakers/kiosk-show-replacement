"""
ICS/iCal service module for the Kiosk.show Replacement application.

This module provides services for fetching, caching, and querying iCal/ICS
calendar data. It handles HTTP fetching, database synchronization, and
formatting calendar data for frontend display.
"""

import json
import logging
from datetime import date, datetime, time, timedelta, timezone, tzinfo
from typing import Any, Optional, cast

import requests
from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError

from .ical_parser import parse_ics_data, parse_skedda_summary
from .models import ICalEvent, ICalFeed, SlideshowItem, db

logger = logging.getLogger(__name__)

# Default timeout for HTTP requests (seconds)
DEFAULT_FETCH_TIMEOUT = 30

# Default refresh interval if not specified (minutes)
DEFAULT_REFRESH_MINUTES = 15


def fetch_ics_from_url(url: str, timeout: int = DEFAULT_FETCH_TIMEOUT) -> Optional[str]:
    """Fetch ICS content from a URL.

    Args:
        url: URL of the ICS feed
        timeout: Request timeout in seconds

    Returns:
        ICS content as string, or None if fetch failed
    """
    try:
        response = requests.get(
            url,
            timeout=timeout,
            headers={
                "User-Agent": "KioskShowReplacement/1.0",
                "Accept": "text/calendar, application/ics, */*",
            },
        )
        response.raise_for_status()
        return response.text
    except requests.exceptions.Timeout:
        logger.warning(f"Timeout fetching ICS from {url}")
        return None
    except requests.exceptions.RequestException as e:
        logger.warning(f"Error fetching ICS from {url}: {e}")
        return None


def get_or_create_feed(url: str) -> ICalFeed:
    """Get an existing feed by URL or create a new one.

    Args:
        url: URL of the ICS feed

    Returns:
        ICalFeed instance (existing or newly created)
    """
    # Normalize URL to match model validator behavior
    url = url.strip()

    feed = ICalFeed.query.filter_by(url=url).first()
    if feed:
        return cast(ICalFeed, feed)

    # Create new feed, handling potential race condition
    feed = ICalFeed(url=url)
    db.session.add(feed)
    try:
        db.session.commit()
    except IntegrityError:
        # Another request created the feed concurrently; rollback and fetch it
        db.session.rollback()
        feed = ICalFeed.query.filter_by(url=url).first()
        if feed:
            return cast(ICalFeed, feed)
        # If still not found, re-raise the error
        raise
    return feed


def needs_refresh(feed: ICalFeed, refresh_minutes: int) -> bool:
    """Check if a feed needs to be refreshed.

    Args:
        feed: ICalFeed instance
        refresh_minutes: Refresh interval in minutes

    Returns:
        True if the feed should be refreshed
    """
    if feed.last_fetched is None:
        return True

    # Ensure last_fetched is timezone-aware
    last_fetched = feed.last_fetched
    if last_fetched.tzinfo is None:
        last_fetched = last_fetched.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)
    age = now - last_fetched

    return age > timedelta(minutes=refresh_minutes)


def refresh_feed_if_needed(
    feed: ICalFeed, refresh_minutes: int = DEFAULT_REFRESH_MINUTES
) -> bool:
    """Refresh a feed if it's stale.

    Args:
        feed: ICalFeed instance
        refresh_minutes: Refresh interval in minutes

    Returns:
        True if the feed was refreshed, False otherwise
    """
    if not needs_refresh(feed, refresh_minutes):
        return False

    return refresh_feed(feed)


def refresh_feed(feed: ICalFeed) -> bool:
    """Force refresh a feed from its URL.

    Args:
        feed: ICalFeed instance

    Returns:
        True if refresh succeeded, False otherwise
    """
    logger.info(f"Refreshing ICS feed: {feed.url}")

    ics_content = fetch_ics_from_url(feed.url)
    if ics_content is None:
        feed.last_error = (
            f"Failed to fetch ICS from URL at {datetime.now(timezone.utc).isoformat()}"
        )
        db.session.commit()
        return False

    try:
        events = parse_ics_data(ics_content)
    except ValueError as e:
        feed.last_error = f"Failed to parse ICS content: {e}"
        db.session.commit()
        logger.warning(f"Failed to parse ICS from {feed.url}: {e}")
        return False

    sync_feed_events(feed, events)
    feed.last_fetched = datetime.now(timezone.utc)
    feed.last_error = None
    db.session.commit()

    logger.info(f"Refreshed ICS feed {feed.url}: {len(events)} events")
    return True


def sync_feed_events(feed: ICalFeed, events: list[dict[str, Any]]) -> None:
    """Synchronize parsed events with the database.

    This performs an upsert operation: existing events are updated,
    new events are created, and events no longer in the feed are deleted.

    Args:
        feed: ICalFeed instance
        events: List of parsed event dictionaries from parse_ics_data()
    """
    # Build a set of UIDs from the new events
    new_uids = {e["uid"] for e in events}

    # Delete events that are no longer in the feed
    ICalEvent.query.filter(
        and_(ICalEvent.feed_id == feed.id, ~ICalEvent.uid.in_(new_uids))
    ).delete(synchronize_session=False)

    # Upsert each event
    for event_data in events:
        existing = ICalEvent.query.filter_by(
            feed_id=feed.id, uid=event_data["uid"]
        ).first()

        if existing:
            # Update existing event
            existing.summary = event_data["summary"]
            existing.description = event_data["description"]
            existing.start_time = event_data["start_time"]
            existing.end_time = event_data["end_time"]
            existing.resources = json.dumps(event_data["resources"])
            existing.attendee_name = event_data["attendee_name"]
            existing.attendee_email = event_data["attendee_email"]
        else:
            # Create new event
            new_event = ICalEvent(
                feed_id=feed.id,
                uid=event_data["uid"],
                summary=event_data["summary"],
                description=event_data["description"],
                start_time=event_data["start_time"],
                end_time=event_data["end_time"],
                resources=json.dumps(event_data["resources"]),
                attendee_name=event_data["attendee_name"],
                attendee_email=event_data["attendee_email"],
            )
            db.session.add(new_event)


def get_events_for_date(
    feed: ICalFeed, target_date: date, tz: Optional[tzinfo] = None
) -> list[ICalEvent]:
    """Get all events for a specific date from a feed.

    Args:
        feed: ICalFeed instance
        target_date: Date to query events for
        tz: Timezone for interpreting the date boundaries. If None, uses the
            system local timezone (set via TZ env var or /etc/localtime).

    Returns:
        List of ICalEvent instances for the given date
    """
    if tz is None:
        tz = _get_local_tz()

    # Create datetime range for the target date in local timezone,
    # then convert to UTC for the DB query
    day_start = datetime.combine(target_date, time.min).replace(tzinfo=tz)
    day_end = datetime.combine(target_date, time.max).replace(tzinfo=tz)
    day_start = day_start.astimezone(timezone.utc)
    day_end = day_end.astimezone(timezone.utc)

    # Query events that overlap with the target date
    # An event overlaps if: start_time < day_end AND end_time > day_start
    events = (
        ICalEvent.query.filter(
            and_(
                ICalEvent.feed_id == feed.id,
                ICalEvent.start_time < day_end,
                ICalEvent.end_time > day_start,
            )
        )
        .order_by(ICalEvent.start_time)
        .all()
    )

    return cast(list[ICalEvent], events)


def get_all_feed_spaces(feed: ICalFeed) -> list[str]:
    """Get all unique space/resource names from all events in a feed.

    Args:
        feed: ICalFeed instance

    Returns:
        Sorted list of unique space/resource names
    """
    events = ICalEvent.query.filter(
        ICalEvent.feed_id == feed.id,
        ICalEvent.resources.isnot(None),
    ).all()

    spaces_set: set[str] = set()
    for event in events:
        try:
            resources = json.loads(event.resources) if event.resources else []
            spaces_set.update(resources)
        except json.JSONDecodeError, TypeError:
            pass

    return sorted(spaces_set)


def get_skedda_calendar_data(
    slide: SlideshowItem, target_date: Optional[date] = None
) -> dict[str, Any]:
    """Get formatted Skedda calendar data for a slideshow item.

    This is the main function for the frontend to retrieve calendar data.
    It handles cache refresh and formats the data for display.

    Args:
        slide: SlideshowItem with content_type='skedda'
        target_date: Date to display (defaults to today in local timezone)

    Returns:
        Dictionary with formatted calendar data:
        {
            "date": "2026-01-28",
            "date_display": "Wednesday, January 28, 2026",
            "spaces": ["CNC Milling Machine", "Laser Cutter", ...],
            "time_slots": [
                {"time": "07:00", "display": "7:00 AM"},
                ...
            ],
            "events": [
                {
                    "id": 123,
                    "space": "Laser Cutter",
                    "person_name": "John Doe",
                    "description": "Project",
                    "start_time": "12:00",
                    "end_time": "14:00",
                    "start_slot": 10,
                    "row_span": 4
                },
                ...
            ],
            "last_updated": "2026-01-28T10:30:00Z"
        }

    Raises:
        ValueError: If slide is not a skedda type or has no feed
    """
    if slide.content_type != "skedda":
        raise ValueError(f"Slide {slide.id} is not a skedda type")

    if not slide.ical_feed_id or not slide.ical_feed:
        raise ValueError(f"Slide {slide.id} has no iCal feed configured")

    feed = slide.ical_feed
    refresh_minutes = slide.ical_refresh_minutes or DEFAULT_REFRESH_MINUTES

    # Refresh if needed
    refresh_feed_if_needed(feed, refresh_minutes)

    # Determine local timezone for display
    local_tz = _get_local_tz()

    # Use today in local timezone if no date specified
    if target_date is None:
        target_date = datetime.now(local_tz).date()

    # Get events for the date using local timezone boundaries
    events = get_events_for_date(feed, target_date, tz=local_tz)

    # Collect all unique spaces from the entire feed (not just today's events)
    # so that columns appear even for spaces with no bookings today
    spaces: list[str] = get_all_feed_spaces(feed)

    # Generate time slots (30-minute intervals, 7 AM to 11 PM)
    time_slots = []
    for hour in range(7, 23):  # 7 AM to 10:30 PM
        for minute in [0, 30]:
            slot_time = time(hour, minute)
            time_slots.append(
                {
                    "time": slot_time.strftime("%H:%M"),
                    "display": slot_time.strftime("%-I:%M %p"),
                }
            )

    # Format events for display
    formatted_events = []
    for event in events:
        try:
            resources = json.loads(event.resources) if event.resources else []
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(
                "Invalid resources JSON for event %s (uid=%s): %s",
                event.id,
                event.uid,
                e,
            )
            resources = []

        # Parse Skedda summary for display info
        person_name, description, _ = parse_skedda_summary(event.summary)

        # If no person name from summary, use attendee name
        if not person_name and event.attendee_name:
            person_name = event.attendee_name

        # Convert event times from UTC to local timezone for display
        local_start = event.start_time.replace(tzinfo=timezone.utc).astimezone(local_tz)
        local_end = event.end_time.replace(tzinfo=timezone.utc).astimezone(local_tz)

        # Calculate slot positions using local times
        start_slot = _time_to_slot_index(local_start)
        end_slot = _time_to_slot_index(local_end)
        row_span = max(1, end_slot - start_slot)

        # Create an event entry for each space
        for space in resources:
            if space in spaces:
                formatted_events.append(
                    {
                        "id": event.id,
                        "uid": event.uid,
                        "space": space,
                        "person_name": person_name or "",
                        "description": description or event.summary,
                        "start_time": local_start.strftime("%H:%M"),
                        "end_time": local_end.strftime("%H:%M"),
                        "start_slot": start_slot,
                        "row_span": row_span,
                    }
                )

    return {
        "date": target_date.isoformat(),
        "date_display": target_date.strftime("%A, %B %d, %Y"),
        "spaces": spaces,
        "time_slots": time_slots,
        "events": formatted_events,
        "last_updated": (
            feed.last_fetched.replace(tzinfo=timezone.utc).isoformat()
            if feed.last_fetched
            else None
        ),
    }


def _get_local_tz() -> tzinfo:
    """Get the system local timezone.

    This uses the system timezone as configured by the TZ environment variable
    or /etc/localtime. In Docker, set TZ=America/New_York (or similar) in the
    environment.

    Returns:
        A tzinfo instance representing the system local timezone.
    """
    local = datetime.now().astimezone().tzinfo
    assert local is not None
    return local


def _time_to_slot_index(dt: datetime) -> int:
    """Convert a datetime to a slot index (30-minute intervals starting at 7 AM).

    Args:
        dt: Datetime to convert

    Returns:
        Slot index (0 = 7:00 AM, 1 = 7:30 AM, etc.)
    """
    # Extract hour and minute
    hour = dt.hour
    minute = dt.minute

    # Calculate slot index (7 AM = slot 0)
    if hour < 7:
        return 0
    if hour >= 23:
        return 32  # 10:30 PM is the last slot

    slot = (hour - 7) * 2
    if minute >= 30:
        slot += 1

    return slot


def refresh_all_feeds() -> dict[str, Any]:
    """Refresh all ICS feeds in the database.

    Returns:
        Dictionary with refresh results:
        {
            "refreshed": 3,
            "errors": [
                {"feed_id": 2, "url": "...", "error": "..."},
                ...
            ]
        }
    """
    feeds = ICalFeed.query.all()
    refreshed = 0
    errors = []

    for feed in feeds:
        try:
            if refresh_feed(feed):
                refreshed += 1
        except Exception as e:
            logger.exception(f"Error refreshing feed {feed.id}")
            errors.append(
                {
                    "feed_id": feed.id,
                    "url": feed.url,
                    "error": str(e),
                }
            )

    return {
        "refreshed": refreshed,
        "errors": errors,
    }
