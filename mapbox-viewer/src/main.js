import mapboxgl from "mapbox-gl";
import "mapbox-gl/dist/mapbox-gl.css";

// Configuration
const config = {
  // Mapbox public token - replace with your token if needed
  mapboxToken:
    "pk.eyJ1Ijoic25vd2Nhc3QiLCJhIjoiY2plYXNjdTRoMDhsbDJ4bGFjOWN0YjdzeCJ9.fM2s4NZq_LUiTXJxsl2HbQ",

  // TiTiler server URL
  tilerBaseUrl: "http://127.0.0.1:8000",

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

// Get URL parameters
const urlParams = new URLSearchParams(window.location.search);
const dataUrl =
  urlParams.get("url") || "data/LEO-2025-05-01T000000Z_highres_cog.tif";
//   const dataUrl =
//   urlParams.get("url") ||
//   "data/ABI-GOES19-GLOBAL-2025-04-26T170000Z_SST_cog.tif";

//   LEO-2025-05-01T000000Z_SST_cog

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
  // For LEO data converted to Byte (0-255), we need to remap to the actual temperature range
  // Assuming data was scaled from ~22°C to ~27.5°C (71.6°F to 81.5°F) to 0-255
  const celsiusMin = 21.9; // Minimum temperature in dataset in Celsius
  const celsiusMax = 27.54; // Maximum temperature in dataset in Celsius

  // First convert the 0-255 value back to celsius using the linear scale
  const celsius =
    celsiusMin + (parseFloat(raw) / 255) * (celsiusMax - celsiusMin);

  // Then convert celsius to fahrenheit
  return (celsius * 9) / 5 + 32;
}

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
  // Min value slider
  const minValueSlider = document.getElementById("min-value");
  const minValueDisplay = document.getElementById("min-value-display");

  // Update slider min/max to match our data range
  minValueSlider.min = config.temperature.min;
  minValueSlider.max = config.temperature.max;
  minValueSlider.value = config.temperature.min;
  minValueDisplay.textContent = config.temperature.min.toFixed(2);

  minValueSlider.addEventListener("input", (e) => {
    const value = parseFloat(e.target.value);
    // Ensure min doesn't exceed max
    if (value >= config.temperature.max) {
      e.target.value = config.temperature.max - 1;
      config.temperature.min = config.temperature.max - 1;
    } else {
      config.temperature.min = value;
    }
    minValueDisplay.textContent = config.temperature.min.toFixed(2);
    updateRasterLayer();
  });

  // Max value slider
  const maxValueSlider = document.getElementById("max-value");
  const maxValueDisplay = document.getElementById("max-value-display");

  // Update slider min/max to match our data range
  maxValueSlider.min = config.temperature.min;
  maxValueSlider.max = config.temperature.max;
  maxValueSlider.value = config.temperature.max;
  maxValueDisplay.textContent = config.temperature.max.toFixed(2);

  maxValueSlider.addEventListener("input", (e) => {
    const value = parseFloat(e.target.value);
    // Ensure max doesn't go below min
    if (value <= config.temperature.min) {
      e.target.value = config.temperature.min + 1;
      config.temperature.max = config.temperature.min + 1;
    } else {
      config.temperature.max = value;
    }
    maxValueDisplay.textContent = config.temperature.max.toFixed(2);
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

  // Build tile URL with appropriate colormap for temperatures
  const minF = config.temperature.min;
  const maxF = config.temperature.max;
  const rawMin = fahrenheitToRaw(minF);
  const rawMax = fahrenheitToRaw(maxF);

  // Use our custom high-contrast SST colormap
  const colormap = "sst_high_contrast"; // Use our custom colormap defined in TiTiler

  const searchParams = new URLSearchParams({
    url: dataUrl,
    rescale: `${rawMin},${rawMax}`,
    colormap_name: colormap,
    resampling: "bilinear",
  });
  const tileUrl = `${
    config.tilerBaseUrl
  }/cog/tiles/WebMercatorQuad/{z}/{x}/{y}?${searchParams.toString()}`;

  // Debug logs
  console.log(`Temperature range: ${minF.toFixed(2)}°F - ${maxF.toFixed(2)}°F`);
  console.log(`Raw data range: ${rawMin} - ${rawMax} (0-255 scale)`);
  console.log(`Using colormap: ${colormap}`);

  // Add the new source and layer
  map.addSource("sst-source", {
    type: "raster",
    tiles: [tileUrl],
    tileSize: 512,
    attribution: "Data: Sea Surface Temperature",
  });
  map.addLayer({
    id: "sst-layer",
    type: "raster",
    source: "sst-source",
    paint: {
      "raster-opacity": 1, // Slightly transparent to see base map
      "raster-resampling": "linear",
    },
  });

  // Update the legend gradient
  updateLegendGradient(minF, maxF, colormap);
}

// Add a new function to update the legend
function updateLegendGradient(min, max, colormap) {
  const legendEl = document.getElementById("gradient");
  if (!legendEl) return;

  // Clear existing gradient
  legendEl.innerHTML = "";

  // Create gradient bar
  const gradientBar = document.createElement("div");
  gradientBar.style.height = "20px";
  gradientBar.style.width = "100%";
  gradientBar.style.marginBottom = "5px";

  // Set gradient based on colormap
  let gradientColors;
  switch (colormap) {
    case "sst_high_contrast":
      // Use our custom high-contrast SST colors
      gradientColors =
        "linear-gradient(to right, #081d58, #0d2167, #122b76, #173584, #1c3f93, #2149a1, #3a7bea, #4185f8, #34d1db, #0effc5, #7ff000, #ebf600, #fec44f, #fdb347, #fca23f, #fb9137, #fa802f, #f96f27, #f85e1f, #f74d17)";
      break;
    case "rdylbu_r":
      gradientColors =
        "linear-gradient(to right, #313695, #4575b4, #74add1, #abd9e9, #e0f3f8, #ffffbf, #fee090, #fdae61, #f46d43, #d73027, #a50026)";
      break;
    case "turbo":
      gradientColors =
        "linear-gradient(to right, #30123b, #4145ab, #4675ed, #39a7ff, #1bcfd4, #24eb7a, #6df643, #aefa12, #e7f205, #fac825, #f8870f, #ca3e02, #782003)";
      break;
    default:
      gradientColors =
        "linear-gradient(to right, #313695, #4575b4, #74add1, #abd9e9, #e0f3f8, #fee090, #fdae61, #f46d43, #d73027, #a50026)";
  }

  gradientBar.style.background = gradientColors;
  legendEl.appendChild(gradientBar);

  // Add min/max labels
  const labels = document.createElement("div");
  labels.style.display = "flex";
  labels.style.justifyContent = "space-between";

  const minLabel = document.createElement("span");
  minLabel.textContent = `${min.toFixed(1)}°F`;

  const maxLabel = document.createElement("span");
  maxLabel.textContent = `${max.toFixed(1)}°F`;

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
