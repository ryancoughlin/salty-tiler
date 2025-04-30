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

  // Initial rendering parameters
  initialParams: {
    colormap_name: "viridis",
    rescale: "0,3778", // 32°F to 100°F
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

// Function to build the TiTiler URL for COG tiles
function buildTilerUrl(z, x, y, params = {}) {
  const allParams = {
    url: dataUrl,
    ...config.initialParams,
    ...params,
  };

  const searchParams = new URLSearchParams();
  Object.entries(allParams).forEach(([key, value]) => {
    if (key === "colormap") {
      searchParams.append("colormap_name", value);
    } else {
      searchParams.append(key, value);
    }
  });

  return `${
    config.tilerBaseUrl
  }/cog/tiles/WebMercatorQuad/${z}/${x}/${y}?${searchParams.toString()}`;
}

// Function to display error messages
function showError(message) {
  const errorEl = document.getElementById("error-message");
  errorEl.textContent = message;
  errorEl.style.display = "block";

  // Auto-hide after 5 seconds
  setTimeout(() => {
    errorEl.style.display = "none";
  }, 5000);
}

// Function to update the raster layer
function updateRasterLayer(params = {}) {
  // Remove existing layer and source if they exist
  if (map.getLayer("sst-layer")) {
    map.removeLayer("sst-layer");
  }
  if (map.getSource("sst-source")) {
    map.removeSource("sst-source");
  }

  // Build the tile URL using COG endpoint
  const tileUrl = buildTilerUrl("{z}", "{x}", "{y}", params);

  // Update the debug URL display
  document.getElementById("titiler-url").textContent = config.tilerBaseUrl;

  // Add new source and layer
  try {
    map.addSource("sst-source", {
      type: "raster",
      tiles: [tileUrl],
      tileSize: 256,
      attribution: "Data: NOAA/NESDIS GOES19 ABI Sea Surface Temperature",
    });

    map.addLayer({
      id: "sst-layer",
      type: "raster",
      source: "sst-source",
      paint: {
        "raster-opacity": 0.8,
        "raster-resampling": "linear",
      },
    });

    // Update legend
    updateLegend(
      params.colormap_name || config.initialParams.colormap_name,
      params.rescale
        ? params.rescale.split(",")[0]
        : config.initialParams.rescale.split(",")[0],
      params.rescale
        ? params.rescale.split(",")[1]
        : config.initialParams.rescale.split(",")[1]
    );
  } catch (error) {
    showError(`Error loading tiles: ${error.message}`);
    console.error("Error loading tiles:", error);
  }
}

// Generate a gradient for the legend
function updateLegend(colormap, vmin, vmax) {
  const legendEl = document.getElementById("gradient");
  const numSteps = 10;
  let gradientHtml = "";

  // Update the legend title for Sea Surface Temperature
  document.querySelector("#legend h3").textContent =
    "Sea Surface Temperature (°F)";

  // Create legend items
  for (let i = 0; i < numSteps; i++) {
    const step = i / (numSteps - 1);
    const value =
      parseFloat(vmin) + step * (parseFloat(vmax) - parseFloat(vmin));

    // Approximate the colors based on the colormap
    let color;

    switch (colormap) {
      case "viridis":
        color = getViridisColor(step);
        break;
      case "plasma":
        color = getPlasmaColor(step);
        break;
      case "turbo":
        color = getTurboColor(step);
        break;
      case "jet":
        color = getJetColor(step);
        break;
      case "rainbow":
        color = getRainbowColor(step);
        break;
      default:
        color = getViridisColor(step);
    }

    gradientHtml += `
      <div style="display: flex; align-items: center; margin-bottom: 5px;">
        <span class="legend-key" style="background-color: ${color};"></span>
        <span>${value.toFixed(2)}</span>
      </div>
    `;
  }

  legendEl.innerHTML = gradientHtml;
}

// Color approximation functions for legend (simplified)
function getViridisColor(t) {
  // Viridis approx: dark blue -> purple -> green -> yellow
  return `rgb(${Math.floor(t * 255)}, ${Math.floor(t * 150 + 50)}, ${Math.floor(
    255 * (1 - t)
  )})`;
}

function getPlasmaColor(t) {
  // Plasma approx: dark purple -> pink -> orange -> yellow
  return `rgb(${Math.floor(t * 255)}, ${Math.floor(t * 100)}, ${Math.floor(
    255 * (1 - t * 0.8)
  )})`;
}

function getTurboColor(t) {
  // Turbo approx: blue -> cyan -> green -> yellow -> red
  const r = Math.sin(t * Math.PI) * 255;
  const g = Math.sin((t + 0.33) * Math.PI) * 255;
  const b = Math.sin((t + 0.66) * Math.PI) * 255;
  return `rgb(${Math.floor(r)}, ${Math.floor(g)}, ${Math.floor(b)})`;
}

function getJetColor(t) {
  // Jet approx: blue -> cyan -> yellow -> red
  const r = t < 0.5 ? 0 : (t - 0.5) * 2 * 255;
  const g = t < 0.5 ? t * 2 * 255 : (1 - t) * 2 * 255;
  const b = t < 0.5 ? 255 * (1 - t * 2) : 0;
  return `rgb(${Math.floor(r)}, ${Math.floor(g)}, ${Math.floor(b)})`;
}

function getRainbowColor(t) {
  // Rainbow approx: red -> yellow -> green -> cyan -> blue -> magenta
  const r = Math.sin(t * Math.PI) * 255;
  const g = Math.sin((t + 0.33) * Math.PI) * 255;
  const b = Math.sin((t + 0.66) * Math.PI) * 255;
  return `rgb(${Math.floor(r)}, ${Math.floor(g)}, ${Math.floor(b)})`;
}

// Function to fetch COG metadata
async function fetchCogMetadata() {
  try {
    const response = await fetch(
      `${config.tilerBaseUrl}/cog/info?url=${encodeURIComponent(dataUrl)}`
    );

    if (!response.ok) {
      throw new Error(
        `Metadata request failed with status: ${response.status}`
      );
    }

    const metadata = await response.json();
    console.log("COG metadata:", metadata);

    // Update the controls based on the metadata
    document.getElementById("colormap").value =
      config.initialParams.colormap_name;

    // Disable NetCDF-specific controls
    document.getElementById("time-idx").disabled = true;
    document.getElementById("level-idx").disabled = true;

    // Get min/max values from metadata if available
    if (metadata.statistics && metadata.statistics[1]) {
      const stats = metadata.statistics[1];
      if (stats.min !== undefined && stats.max !== undefined) {
        const minVal = parseFloat(stats.min) || 32;
        const maxVal = parseFloat(stats.max) || 100;

        document.getElementById("min-value").value = minVal;
        document.getElementById("max-value").value = maxVal;

        // Update rescale parameter
        config.initialParams.rescale = `${minVal},${maxVal}`;
      }
    }
  } catch (error) {
    console.error("Error fetching COG metadata:", error);
    showError(`Error fetching COG metadata: ${error.message}`);
  }
}

// Initialize map and add controls
map.on("load", () => {
  // Fetch COG metadata
  fetchCogMetadata();

  // Add raster layer
  updateRasterLayer();

  // Set up event listeners for controls
  document.getElementById("update-layer").addEventListener("click", () => {
    const colormap = document.getElementById("colormap").value;
    const minValue = document.getElementById("min-value").value;
    const maxValue = document.getElementById("max-value").value;

    updateRasterLayer({
      colormap_name: colormap,
      rescale: `${minValue},${maxValue}`,
      color_formula: "gamma rgb 1.3,sigmoidal rgb 22 0.1",
    });
  });

  // Add navigation controls
  map.addControl(new mapboxgl.NavigationControl(), "top-left");
});
