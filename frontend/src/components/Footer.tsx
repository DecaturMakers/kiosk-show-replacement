import React, { useState, useEffect } from 'react';

const VERSION_ENDPOINT = '/api/v1/version';

const fetchVersionWithTimeout = async (timeoutMs = 5000): Promise<string | null> => {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(VERSION_ENDPOINT, { signal: controller.signal });
    if (!response.ok) {
      console.error(`Failed to fetch version: HTTP ${response.status}`);
      return null;
    }

    const data = await response.json();
    if (data?.data?.version && typeof data.data.version === 'string') {
      return data.data.version;
    }

    console.error('Unexpected version response shape:', data);
    return null;
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') {
      console.error(`Version fetch timed out after ${timeoutMs}ms`);
    } else {
      console.error('Error fetching version:', error);
    }
    return null;
  } finally {
    window.clearTimeout(timeoutId);
  }
};

const Footer: React.FC = () => {
  const [version, setVersion] = useState<string>('');

  useEffect(() => {
    let isMounted = true;

    const loadVersion = async (): Promise<void> => {
      const fetchedVersion = await fetchVersionWithTimeout();
      if (isMounted && fetchedVersion) {
        setVersion(fetchedVersion);
      }
    };

    void loadVersion();

    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <footer className="bg-light mt-5 py-4">
      <div className="container text-center">
        <p className="text-muted mb-0">
          <a
            href="https://github.com/Decaturmakers/kiosk-show-replacement"
            target="_blank"
            rel="noopener noreferrer"
          >
            kiosk-show-replacement{version ? ` v${version}` : ''}
          </a>{' '}
          is{' '}
          <a
            href="https://opensource.org/license/mit"
            target="_blank"
            rel="noopener noreferrer"
          >
            Free and Open Source Software
          </a>
          , Copyright 2026 Jason Antman / Decatur Makers.
        </p>
      </div>
    </footer>
  );
};

export default Footer;
