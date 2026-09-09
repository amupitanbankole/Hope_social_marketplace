# HopeSocial Marketplace — Full-Stack Monorepo

HopeSocial Marketplace is a premium full-stack application built with a **Next.js (JavaScript & JSX) Frontend** and a **Python & Django REST Framework Backend**.

## Project Structure

```text
social-hub-marketplace/
├── frontend/             <-- Next.js (JS/JSX) Web Application
│   ├── src/
│   └── package.json
├── backend/              <-- Python & Django REST API Server
│   ├── manage.py
│   ├── core/             <-- Django settings & URLs
│   ├── users/            <-- User Auth & Wallet Model
│   └── marketplace/      <-- Services, Products, Accounts, Orders, Transactions
├── package.json
├── .gitignore
└── README.md
```

## Marketreum catalog integration

The Social Marketplace now supports importing an external Marketreum catalog into the existing `Service` model. This preserves the current marketplace cards, platform buttons, category labels, search, pagination and order UI instead of replacing the existing template.

### Environment variables

Configure these **server-side only** in the backend hosting environment. Do not place the Marketreum API key in the Next.js frontend.

```env
MARKETREUM_API_URL=https://your-marketreum-api.example.com
MARKETREUM_API_KEY=replace-with-server-side-api-key
MARKETREUM_PROVIDER_NAME=Marketreum
MARKETREUM_MARGIN_PERCENTAGE=30
MARKETREUM_AUTH_HEADER=Authorization
MARKETREUM_AUTH_SCHEME=Bearer
MARKETREUM_SERVICES_PATH=/services
MARKETREUM_PRODUCTS_PATH=/products
MARKETREUM_TIMEOUT=20
```

The endpoint paths and authentication header/scheme are configurable because a public Marketreum API specification was not discoverable from the repository or public web search. Once the exact Marketreum API documentation is supplied, these values should be aligned to the provider's documented endpoints and request format.

### Database migration

Run:

```bash
python manage.py migrate
```

The migration adds:

- `listing_type` — `service` or `product`
- `external_url` — Marketreum product/service URL
- `image_url` — optional external image URL

### Import Marketreum products and services

```bash
python manage.py sync_marketreum
```

Optional markup override:

```bash
python manage.py sync_marketreum --margin 35
```

Deactivate items that disappeared from the Marketreum catalog:

```bash
python manage.py sync_marketreum --deactivate-missing
```

The sync command normalizes common provider response shapes, applies the configured markup, and maps common social-platform names such as Instagram, Facebook, TikTok, X/Twitter, Telegram, Discord, YouTube, LinkedIn, Pinterest and Snapchat to the existing HopeSocial platform labels. Those labels are what the current Social Marketplace quick-filter buttons use.

### Current ordering behavior

The imported catalog is ready for display and classification. The existing order flow still uses the project's current SMM provider adapter for fulfillment. The Marketreum **ordering** endpoint must not be assumed until its official order/create-order API specification is supplied. This avoids sending an incompatible payload to Marketreum and creating false completed orders.

## Quick Start

To run **both the Django Backend and Next.js Frontend together**:

```bash
npm run dev
```

- **Frontend App**: `http://localhost:3000`
- **Backend API**: `http://127.0.0.1:8000/`
- **Django Admin**: `http://127.0.0.1:8000/admin/`

## Individual Development Commands

### Start Frontend Only

```bash
npm run dev:frontend
```

### Start Backend Only

```bash
npm run dev:backend
```

## Single Git Push

Both `frontend/` and `backend/` are tracked together under a single Git repository:

```bash
git add .
git commit -m "Update full-stack application"
git push origin main
```
