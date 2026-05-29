import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

const sidebars: SidebarsConfig = {
  docsSidebar: [
    'index',
    {
      type: 'category',
      label: 'Getting started',
      collapsed: false,
      items: [
        'getting-started/install',
        'getting-started/quick-start',
        'getting-started/existing-server',
        'getting-started/migrate',
      ],
    },
    {
      type: 'category',
      label: 'Command reference',
      items: [
        'commands/overview',
        'commands/site',
        'commands/nginx-control',
        'commands/backup',
        'commands/cert',
        'commands/security',
        'commands/observability',
        'commands/preset',
        'commands/cluster',
        'commands/dashboard',
        'commands/update',
        'commands/admin',
      ],
    },
    {
      type: 'category',
      label: 'Guides',
      items: [
        'guides/wordpress',
        'guides/laravel',
        'guides/node',
        'guides/static-sites',
        'guides/wildcard-cert',
        'guides/cloudflare',
        'guides/multi-server',
      ],
    },
    {
      type: 'category',
      label: 'Operations',
      items: [
        'operations/safety',
        'operations/backup-restore',
        'operations/updates',
        'operations/cautions',
        'operations/troubleshooting',
      ],
    },
    'architecture',
    'comparison',
    'changelog',
  ],
};

export default sidebars;
