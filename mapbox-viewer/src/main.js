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

  // Temperature range in Fahrenheit (calculated from 21.9°C to 27.54°C)
  temperature: {
    min: 71.4, // 21.9°C in Fahrenheit
    max: 81.6, // 27.54°C in Fahrenheit
  },
};

// Dataset configs
const DATASETS = {
  sst: {
    label: "Sea Surface Temperature",
    dataUrl: "cogs/sea_surface_temperature_LEO-2025-05-01T000000Z_F_cog.tif",
    colormap: "sst_high_contrast",
    min: 71.4,
    max: 81.6,
    units: "°F",
    legend:
      "linear-gradient(to right, #081d58, #0d2167, #122b76, #173584, #1c3f93, #2149a1, #3a7bea, #4185f8, #34d1db, #0effc5, #7ff000, #ebf600, #fec44f, #fdb347, #fca23f, #fb9137, #fa802f, #f96f27, #f85e1f, #f74d17)",
  },
  chlorophyll: {
    label: "Chlorophyll",
    dataUrl: "cogs/chlor_a_2025-04-29T000000Z_F_cog.tif",
    colormap: "turbo", // or your custom chlorophyll colormap name
    min: 0.01,
    max: 10,
    units: "mg/m³",
    legend:
      "linear-gradient(to right, #30123b, #4145ab, #4675ed, #39a7ff, #1bcfd4, #24eb7a, #6df643, #aefa12, #e7f205, #fac825, #f8870f, #ca3e02, #782003)",
  },
};

let currentDataset = "sst";

// Set mapbox token
mapboxgl.accessToken = config.mapboxToken;

// Initialize the map
const map = new mapboxgl.Map({
  container: "map",
  style: "mapbox://styles/snowcast/cm3rd1mik008801s97a8db8w6",
  center: config.initialView.center,
  zoom: config.initialView.zoom,
});

function fahrenheitToRaw(f) {
  // Convert fahrenheit to celsius
  const celsius = ((parseFloat(f) - 32) * 5) / 9;

  // Map celsius back to the 0-255 range
  const celsiusMin = 21.9;
  const celsiusMax = 27.54;

  // Ensure value is within valid range
  const clampedCelsius = Math.max(celsiusMin, Math.min(celsiusMax, celsius));

  // Convert to 0-255 range
  return Math.round(
    ((clampedCelsius - celsiusMin) / (celsiusMax - celsiusMin)) * 255
  );
}

// --- UI Setup ---
function setupControls() {
  // Dataset selector
  const datasetSelect = document.getElementById("dataset-select");
  datasetSelect.value = currentDataset;
  datasetSelect.addEventListener("change", (e) => {
    currentDataset = e.target.value;
    updateSlidersForDataset();
    updateRasterLayer();
  });

  // Min value slider
  const minValueSlider = document.getElementById("min-value");
  const minValueDisplay = document.getElementById("min-value-display");
  minValueSlider.addEventListener("input", (e) => {
    const value = parseFloat(e.target.value);
    if (value >= DATASETS[currentDataset].max) {
      e.target.value = DATASETS[currentDataset].max - 1;
      DATASETS[currentDataset].min = DATASETS[currentDataset].max - 1;
    } else {
      DATASETS[currentDataset].min = value;
    }
    minValueDisplay.textContent = DATASETS[currentDataset].min.toFixed(2);
    updateRasterLayer();
  });

  // Max value slider
  const maxValueSlider = document.getElementById("max-value");
  const maxValueDisplay = document.getElementById("max-value-display");
  maxValueSlider.addEventListener("input", (e) => {
    const value = parseFloat(e.target.value);
    if (value <= DATASETS[currentDataset].min) {
      e.target.value = DATASETS[currentDataset].min + 1;
      DATASETS[currentDataset].max = DATASETS[currentDataset].min + 1;
    } else {
      DATASETS[currentDataset].max = value;
    }
    maxValueDisplay.textContent = DATASETS[currentDataset].max.toFixed(2);
    updateRasterLayer();
  });

  // Update button
  const updateButton = document.getElementById("update-layer");
  updateButton.addEventListener("click", updateRasterLayer);

  updateSlidersForDataset();
}

function updateSlidersForDataset() {
  const minValueSlider = document.getElementById("min-value");
  const minValueDisplay = document.getElementById("min-value-display");
  const maxValueSlider = document.getElementById("max-value");
  const maxValueDisplay = document.getElementById("max-value-display");
  const ds = DATASETS[currentDataset];
  minValueSlider.min = ds.min;
  minValueSlider.max = ds.max;
  minValueSlider.value = ds.min;
  minValueDisplay.textContent = ds.min.toFixed(2);
  maxValueSlider.min = ds.min;
  maxValueSlider.max = ds.max;
  maxValueSlider.value = ds.max;
  maxValueDisplay.textContent = ds.max.toFixed(2);
}

// --- Raster Layer Update ---
function updateRasterLayer() {
  if (map.getLayer("data-layer")) map.removeLayer("data-layer");
  if (map.getSource("data-source")) map.removeSource("data-source");
  const ds = DATASETS[currentDataset];
  const min = ds.min;
  const max = ds.max;
  const colormap = ds.colormap;
  const dataUrl = ds.dataUrl;
  const searchParams = new URLSearchParams({
    url: dataUrl,
    rescale: `${min},${max}`,
    colormap_name: colormap,
    resampling: "bilinear",
  });
  const tileUrl = `${
    config.tilerBaseUrl
  }/cog/tiles/WebMercatorQuad/{z}/{x}/{y}.png?${searchParams.toString()}`;
  map.addSource("data-source", {
    type: "raster",
    tiles: [tileUrl],
    tileSize: 512,
    attribution: `Data: ${ds.label}`,
  });
  map.addLayer({
    id: "data-layer",
    type: "raster",
    source: "data-source",
    paint: {
      "raster-opacity": 1,
      "raster-resampling": "linear",
    },
    slot: "middle",
  });
  updateLegendGradient(min, max, colormap, ds);
}

function updateLegendGradient(min, max, colormap, ds) {
  const legendEl = document.getElementById("gradient");
  if (!legendEl) return;
  legendEl.innerHTML = "";
  const gradientBar = document.createElement("div");
  gradientBar.style.height = "20px";
  gradientBar.style.width = "100%";
  gradientBar.style.marginBottom = "5px";
  gradientBar.style.background = ds.legend;
  legendEl.appendChild(gradientBar);
  const labels = document.createElement("div");
  labels.style.display = "flex";
  labels.style.justifyContent = "space-between";
  const minLabel = document.createElement("span");
  minLabel.textContent = `${min.toFixed(2)} ${ds.units}`;
  const maxLabel = document.createElement("span");
  maxLabel.textContent = `${max.toFixed(2)} ${ds.units}`;
  labels.appendChild(minLabel);
  labels.appendChild(maxLabel);
  legendEl.appendChild(labels);
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
