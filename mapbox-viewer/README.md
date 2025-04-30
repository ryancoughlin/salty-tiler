# Chlorophyll Concentration Mapbox Viewer

A Vite + Mapbox GL JS v3 application for visualizing chlorophyll concentration data served by TiTiler from NetCDF files.

## Prerequisites

- Node.js (v14+)
- TiTiler server running at http://localhost:8000 with chlorophyll NetCDF data

## Setup

1. Install dependencies:

```bash
cd mapbox-viewer
npm install
```

2. Start the development server:

```bash
npm run dev
```

This will open the application in your browser at http://localhost:3000.

## Features

- Interactive map visualization of chlorophyll concentration data
- Customizable colormaps (viridis, plasma, turbo, jet, rainbow)
- Adjustable min/max value range for better data visualization
- Dynamic legend that updates with the selected colormap
- Responsive layout that works on desktop and mobile devices

## Configuration

Edit `src/main.js` to change:

- Map default view (center, zoom)
- TiTiler server URL
- Default variable name
- Default rendering parameters (colormap, value range)

## Building for Production

To build for production:

```bash
npm run build
```

The built files will be in the `dist` directory, ready to be deployed to a static hosting service.

## License

MIT
