import type {ReactNode} from 'react';
import clsx from 'clsx';
import Heading from '@theme/Heading';
import styles from './styles.module.css';

type FeatureItem = {
  title: string;
  emoji: string;
  description: ReactNode;
};

const FeatureList: FeatureItem[] = [
  {
    title: 'Beginner-friendly CLI',
    emoji: '🧭',
    description: (
      <>
        One <code>easynginx</code> command for create, edit, info, logs, audit,
        backup and more. Interactive prompts when you skip flags. Sensible
        defaults at every step.
      </>
    ),
  },
  {
    title: 'Works on every distro',
    emoji: '🐧',
    description: (
      <>
        Ubuntu, Debian, Fedora, RHEL, Rocky, AlmaLinux, Arch, Manjaro. The
        installer handles package managers, EPEL, firewalls and systemd for you.
      </>
    ),
  },
  {
    title: 'Safe by design',
    emoji: '🛡️',
    description: (
      <>
        Every config write is snapshot &rarr; write &rarr; <code>nginx -t</code>{' '}
        &rarr; reload. Validation failure means automatic rollback. nginx is
        never reloaded with a broken config.
      </>
    ),
  },
  {
    title: 'Backups baked in',
    emoji: '📦',
    description: (
      <>
        Tarball with sha256 manifest. Restore on the same server, a new server,
        or as part of a fresh <code>install.sh</code> run. Cross-distro restore
        works.
      </>
    ),
  },
  {
    title: 'Auto-updates without surprises',
    emoji: '⬆️',
    description: (
      <>
        Background 24h check, atomic engine swap, one-command rollback. Updates
        only touch engine files — your nginx configs and certs are never
        changed by an update.
      </>
    ),
  },
  {
    title: 'Hardening you would otherwise skip',
    emoji: '🔒',
    description: (
      <>
        Audit, TLS profiles, HSTS, bot blocker, GeoIP allow/deny, fail2ban,
        ModSecurity, per-site WAF toggle. All a single command away.
      </>
    ),
  },
];

function Feature({title, emoji, description}: FeatureItem) {
  return (
    <div className={clsx('col col--4', styles.featureCol)}>
      <div className="text--center">
        <span className={styles.featureEmoji} role="img" aria-label={title}>
          {emoji}
        </span>
      </div>
      <div className="text--center padding-horiz--md">
        <Heading as="h3">{title}</Heading>
        <p>{description}</p>
      </div>
    </div>
  );
}

export default function HomepageFeatures(): ReactNode {
  return (
    <section className={styles.features}>
      <div className="container">
        <div className="row">
          {FeatureList.map((props, idx) => (
            <Feature key={idx} {...props} />
          ))}
        </div>
      </div>
    </section>
  );
}
