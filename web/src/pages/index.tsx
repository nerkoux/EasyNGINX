import type {ReactNode} from 'react';
import clsx from 'clsx';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import HomepageFeatures from '@site/src/components/HomepageFeatures';
import Heading from '@theme/Heading';

import styles from './index.module.css';

function HomepageHeader() {
  const {siteConfig} = useDocusaurusContext();
  return (
    <header className={clsx('hero hero--primary', styles.heroBanner)}>
      <div className="container">
        <Heading as="h1" className="hero__title">
          {siteConfig.title}
        </Heading>
        <p className="hero__subtitle">{siteConfig.tagline}</p>
        <p className={styles.heroLead}>
          One installer. One command. Every Linux distro. EasyNginx walks beginners
          through reverse proxies, static sites, PHP, WebSockets, SSL, security
          hardening and backups, and rolls back automatically when anything goes
          wrong.
        </p>
        <div className={styles.buttons}>
          <Link
            className="button button--secondary button--lg"
            to="/docs/getting-started/install">
            Get started
          </Link>
          <Link
            className="button button--outline button--lg"
            style={{marginLeft: '0.75rem'}}
            to="/docs/commands/overview">
            Command reference
          </Link>
          <Link
            className="button button--outline button--lg"
            style={{marginLeft: '0.75rem'}}
            href="https://github.com/nerkoux/EasyNGINX">
            GitHub
          </Link>
        </div>
        <pre className={styles.installCommand}>
{`curl -fsSL https://raw.githubusercontent.com/nerkoux/EasyNGINX/main/install.sh | sudo bash`}
        </pre>
      </div>
    </header>
  );
}

export default function Home(): ReactNode {
  const {siteConfig} = useDocusaurusContext();
  return (
    <Layout
      title={`${siteConfig.title} — ${siteConfig.tagline}`}
      description="EasyNginx is a friendly CLI that turns nginx into something a beginner can use without breaking their server.">
      <HomepageHeader />
      <main>
        <HomepageFeatures />
      </main>
    </Layout>
  );
}
