import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

const config: Config = {
  title: 'EasyNginx',
  tagline: 'Friendly nginx setup for everyone.',
  favicon: 'img/favicon.ico',

  future: {
    v4: true,
  },

  // Update these once the site is live (e.g. https://easynginx.akshatmehta.com).
  url: 'https://easynginx.akshatmehta.com',
  baseUrl: '/',

  organizationName: 'nerkoux',
  projectName: 'EasyNGINX',
  trailingSlash: false,

  onBrokenLinks: 'warn',
  markdown: {
    hooks: {
      onBrokenMarkdownLinks: 'warn',
    },
  },

  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  presets: [
    [
      'classic',
      {
        docs: {
          sidebarPath: './sidebars.ts',
          editUrl: 'https://github.com/nerkoux/EasyNGINX/edit/main/web/',
          showLastUpdateTime: true,
        },
        blog: false,
        theme: {
          customCss: './src/css/custom.css',
        },
      } satisfies Preset.Options,
    ],
  ],

  themeConfig: {
    image: 'img/logo.svg',
    colorMode: {
      respectPrefersColorScheme: true,
    },
    navbar: {
      title: 'EasyNginx',
      logo: {
        alt: 'EasyNginx',
        src: 'img/logo.svg',
      },
      items: [
        {
          type: 'docSidebar',
          sidebarId: 'docsSidebar',
          position: 'left',
          label: 'Docs',
        },
        {
          to: '/docs/commands/overview',
          label: 'Commands',
          position: 'left',
        },
        {
          to: '/docs/changelog',
          label: 'Changelog',
          position: 'left',
        },
        {
          href: 'https://github.com/nerkoux/EasyNGINX',
          label: 'GitHub',
          position: 'right',
        },
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: 'Docs',
          items: [
            {label: 'Getting started', to: '/docs/getting-started/install'},
            {label: 'Quick start',     to: '/docs/getting-started/quick-start'},
            {label: 'Command reference', to: '/docs/commands/overview'},
            {label: 'Architecture',    to: '/docs/architecture'},
          ],
        },
        {
          title: 'Project',
          items: [
            {label: 'GitHub',     href: 'https://github.com/nerkoux/EasyNGINX'},
            {label: 'Releases',   href: 'https://github.com/nerkoux/EasyNGINX/releases'},
            {label: 'Issues',     href: 'https://github.com/nerkoux/EasyNGINX/issues'},
          ],
        },
        {
          title: 'Author',
          items: [
            {label: 'akshatmehta.com', href: 'https://akshatmehta.com'},
            {label: '@nerkoux',        href: 'https://github.com/nerkoux'},
          ],
        },
      ],
      copyright: `Copyright © ${new Date().getFullYear()} Akshat Mehta. EasyNginx is released under MIT.`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
      additionalLanguages: ['bash', 'nginx', 'json', 'yaml', 'python', 'diff'],
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
