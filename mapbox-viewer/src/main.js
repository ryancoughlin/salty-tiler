import mapboxgl from "mapbox-gl";
import "mapbox-gl/dist/mapbox-gl.css";

// Configuration
const config = {
  // Mapbox public token - replace with your token if needed
  mapboxToken:
    "pk.eyJ1Ijoic25vd2Nhc3QiLCJhIjoiY2plYXNjdTRoMDhsbDJ4bGFjOWN0YjdzeCJ9.fM2s4NZq_LUiTXJxsl2HbQ",

  // TiTiler server URL
  tilerBaseUrl: "http://127.0.0.1:8001",

  // Initial map view
  initialView: {
    center: [-95.5, 37], // Center of North America
    zoom: 4,
  },

  // Temperature range in Fahrenheit
  temperature: {
    min: 42.8,
    max: 89.3,
  },
};

// Get URL parameters
const urlParams = new URLSearchParams(window.location.search);
const dataUrl =
  urlParams.get("url") ||
  "data/ABI-GOES19-GLOBAL-2025-04-26T170000Z_SST_cog.tif";

// Set mapbox token
mapboxgl.accessToken = config.mapboxToken;

// Initialize the map
const map = new mapboxgl.Map({
  container: "map",
  style: "mapbox://styles/snowcast/cm3rd1mik008801s97a8db8w6",
  center: config.initialView.center,
  zoom: config.initialView.zoom,
});

// --- Fahrenheit/Raw Conversion ---
function rawToFahrenheit(raw) {
  return (parseFloat(raw) * 0.01 * 9) / 5 + 32;
}
function fahrenheitToRaw(f) {
  return Math.round(((parseFloat(f) - 32) * 5) / 9 / 0.01);
}

// --- UI Setup ---
function setupControls() {
  // Min value slider
  const minValueSlider = document.getElementById("min-value");
  const minValueDisplay = document.getElementById("min-value-display");
  minValueSlider.value = config.temperature.min;
  minValueDisplay.textContent = config.temperature.min;

  minValueSlider.addEventListener("input", (e) => {
    const value = parseFloat(e.target.value);
    // Ensure min doesn't exceed max
    if (value >= config.temperature.max) {
      e.target.value = config.temperature.max - 1;
      config.temperature.min = config.temperature.max - 1;
    } else {
      config.temperature.min = value;
    }
    minValueDisplay.textContent = config.temperature.min;
    updateRasterLayer();
  });

  // Max value slider
  const maxValueSlider = document.getElementById("max-value");
  const maxValueDisplay = document.getElementById("max-value-display");
  maxValueSlider.value = config.temperature.max;
  maxValueDisplay.textContent = config.temperature.max;

  maxValueSlider.addEventListener("input", (e) => {
    const value = parseFloat(e.target.value);
    // Ensure max doesn't go below min
    if (value <= config.temperature.min) {
      e.target.value = config.temperature.min + 1;
      config.temperature.max = config.temperature.min + 1;
    } else {
      config.temperature.max = value;
    }
    maxValueDisplay.textContent = config.temperature.max;
    updateRasterLayer();
  });

  // Update button - now optional since we update in real-time, but keep for explicit refresh
  const updateButton = document.getElementById("update-layer");
  updateButton.addEventListener("click", updateRasterLayer);
}

// --- Raster Layer Update ---
function updateRasterLayer() {
  // Remove existing layer and source if they exist
  if (map.getLayer("sst-layer")) map.removeLayer("sst-layer");
  if (map.getSource("sst-source")) map.removeSource("sst-source");

  // Build tile URL with fixed colormap and rescale
  const minF = config.temperature.min;
  const maxF = config.temperature.max;
  const rawMin = fahrenheitToRaw(minF);
  const rawMax = fahrenheitToRaw(maxF);
  const searchParams = new URLSearchParams({
    url: dataUrl,
    rescale: `${rawMin},${rawMax}`,
    colormap_name: "tempo_r",
    resampling: "bilinear",
  });
  const tileUrl = `${
    config.tilerBaseUrl
  }/cog/tiles/WebMercatorQuad/{z}/{x}/{y}?${searchParams.toString()}`;

  // Debug logs
  console.log(`updateRasterLayer: minF=${minF}, maxF=${maxF}`);
  console.log(`updateRasterLayer: rawMin=${rawMin}, rawMax=${rawMax}`);
  console.log(`updateRasterLayer: tileUrl=${tileUrl}`);

  map.addSource("sst-source", {
    type: "raster",
    tiles: [tileUrl],
    tileSize: 512,
    attribution: "Data: NOAA/NESDIS GOES19 ABI Sea Surface Temperature",
  });
  map.addLayer({
    id: "sst-layer",
    type: "raster",
    source: "sst-source",
    paint: {
      "raster-opacity": 1,
      "raster-resampling": "linear",
    },
  });
}

// --- Error Display ---
function showError(message) {
  const errorEl = document.getElementById("error-message");
  if (errorEl) {
    errorEl.textContent = message;
    errorEl.style.display = "block";
    setTimeout(() => {
      errorEl.style.display = "none";
    }, 5000);
  } else {
    console.error(message);
  }
}

// --- Map Initialization ---
map.on("load", () => {
  setupControls();
  updateRasterLayer();
  map.addControl(new mapboxgl.NavigationControl(), "top-left");
});

// --- UI HTML (for reference, not JS) ---
// <input id="temp-slider" type="range" min="32" max="100" step="0.1">
// <div id="error-message" style="display:none;"></div>
