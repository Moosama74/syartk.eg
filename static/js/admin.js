// MOTORA Admin Portal Javascript

document.addEventListener("DOMContentLoaded", function () {
  // Quick Status changer in vehicle lists
  document.querySelectorAll(".quick-status-select").forEach((select) => {
    select.addEventListener("change", async function () {
      const vehicleId = this.getAttribute("data-vehicle-id");
      const newStatus = this.value;
      const originalColor = this.style.borderColor;

      const fd = new FormData();
      fd.append("status_val", newStatus);

      try {
        const res = await fetch(`/admin/vehicles/${vehicleId}/quick-status`, {
          method: "POST",
          body: fd,
        });
        const data = await res.json();
        if (data.success) {
          this.style.borderColor = "#10b981";
          setTimeout(() => (this.style.borderColor = originalColor), 1500);
        }
      } catch (e) {
        console.error(e);
        this.style.borderColor = "#ef4444";
      }
    });
  });

  // Quick Price updater
  document.querySelectorAll(".quick-price-input").forEach((input) => {
    input.addEventListener("change", async function () {
      const vehicleId = this.getAttribute("data-vehicle-id");
      const newPrice = this.value;

      const fd = new FormData();
      fd.append("price", newPrice);

      try {
        const res = await fetch(`/admin/vehicles/${vehicleId}/quick-price`, {
          method: "POST",
          body: fd,
        });
        const data = await res.json();
        if (data.success) {
          this.classList.add("border-emerald-500");
          setTimeout(() => this.classList.remove("border-emerald-500"), 1500);
        }
      } catch (e) {
        console.error(e);
        this.classList.add("border-red-500");
      }
    });
  });

  // Multi-File Media Uploader on Vehicle Form
  const mediaDropzone = document.getElementById("mediaDropzone");
  const mediaFileInput = document.getElementById("mediaFileInput");
  const mediaPreviewContainer = document.getElementById("mediaPreviewContainer");
  const mediaJsonInput = document.getElementById("media_json");
  const coverImageInput = document.getElementById("cover_image");

  if (mediaDropzone && mediaFileInput && mediaPreviewContainer) {
    let mediaList = [];
    try {
      if (mediaJsonInput && mediaJsonInput.value) {
        mediaList = JSON.parse(mediaJsonInput.value);
      }
    } catch (e) {
      mediaList = [];
    }

    function renderMediaPreviews() {
      mediaPreviewContainer.innerHTML = "";
      mediaList.forEach((item, index) => {
        const card = document.createElement("div");
        card.className =
          "relative group bg-gray-900 border border-gray-800 rounded-lg overflow-hidden p-2 flex flex-col gap-2";

        const isCover = coverImageInput && coverImageInput.value === item.url;

        let mediaTag = "";
        if (item.media_type === "video") {
          mediaTag = `<div class="w-full h-32 bg-black flex items-center justify-center rounded text-gold"><i class="fas fa-video fa-2x"></i></div>`;
        } else {
          mediaTag = `<img src="${item.url}" class="w-full h-32 object-cover rounded" />`;
        }

        card.innerHTML = `
          ${mediaTag}
          <div class="flex items-center justify-between gap-1 text-xs mt-1">
            <button type="button" class="btn-set-cover px-2 py-1 rounded text-xs ${
              isCover
                ? "bg-amber-500 text-black font-bold"
                : "bg-gray-800 hover:bg-gray-700 text-gray-300"
            }" data-index="${index}">
              ${isCover ? "★ الغلاف الرئيسي" : "تعيين كغلاف"}
            </button>
            <button type="button" class="btn-remove-media text-red-400 hover:text-red-300 p-1" data-index="${index}">
              <i class="fas fa-trash"></i>
            </button>
          </div>
          <input type="text" class="media-caption-input w-full bg-gray-950 border border-gray-800 text-xs px-2 py-1 rounded text-gray-300 focus:border-gold outline-none" placeholder="تعليق / وصف الوسيط" value="${
            item.caption || ""
          }" data-index="${index}" />
        `;

        mediaPreviewContainer.appendChild(card);
      });

      // Update JSON input
      if (mediaJsonInput) {
        mediaJsonInput.value = JSON.stringify(mediaList);
      }

      // Attach button events
      mediaPreviewContainer.querySelectorAll(".btn-set-cover").forEach((btn) => {
        btn.addEventListener("click", function () {
          const idx = parseInt(this.getAttribute("data-index"));
          if (coverImageInput && mediaList[idx]) {
            coverImageInput.value = mediaList[idx].url;
            renderMediaPreviews();
          }
        });
      });

      mediaPreviewContainer.querySelectorAll(".btn-remove-media").forEach((btn) => {
        btn.addEventListener("click", function () {
          const idx = parseInt(this.getAttribute("data-index"));
          mediaList.splice(idx, 1);
          if (mediaList.length > 0 && coverImageInput && !mediaList.some((m) => m.url === coverImageInput.value)) {
            coverImageInput.value = mediaList[0].url;
          }
          renderMediaPreviews();
        });
      });

      mediaPreviewContainer.querySelectorAll(".media-caption-input").forEach((inp) => {
        inp.addEventListener("input", function () {
          const idx = parseInt(this.getAttribute("data-index"));
          if (mediaList[idx]) {
            mediaList[idx].caption = this.value;
            if (mediaJsonInput) mediaJsonInput.value = JSON.stringify(mediaList);
          }
        });
      });
    }

    renderMediaPreviews();

    // Trigger file picker
    mediaDropzone.addEventListener("click", () => mediaFileInput.click());

    // File input change
    mediaFileInput.addEventListener("change", async function () {
      if (this.files.length === 0) return;
      const uploadFormData = new FormData();
      for (let i = 0; i < this.files.length; i++) {
        uploadFormData.append("files", this.files[i]);
      }
      uploadFormData.append("category", "vehicles");

      mediaDropzone.innerHTML = `<div class="text-gold py-6"><i class="fas fa-spinner fa-spin mr-2"></i> جاري رفع الصور ومقاطع الفيديو...</div>`;

      try {
        const res = await fetch("/api/media/upload-multiple", {
          method: "POST",
          body: uploadFormData,
        });
        const data = await res.json();
        if (data.success && data.files) {
          data.files.forEach((file) => {
            mediaList.push({
              url: file.url,
              media_type: file.media_type,
              caption: "",
            });
          });

          if (!coverImageInput.value && mediaList.length > 0) {
            coverImageInput.value = mediaList[0].url;
          }

          renderMediaPreviews();
        }
      } catch (err) {
        console.error(err);
        alert("فشل في رفع الوسائط، يرجى المحاولة مرة أخرى.");
      } finally {
        mediaDropzone.innerHTML = `
          <div class="py-6 flex flex-col items-center justify-center text-center cursor-pointer">
            <i class="fas fa-cloud-upload-alt text-3xl text-gold mb-2"></i>
            <p class="text-sm font-semibold text-gray-200">اسحب الصور ومقاطع الفيديو هنا أو اضغط للاختيار من جهازك</p>
            <p class="text-xs text-gray-500 mt-1">يدعم JPG, PNG, WEBP ومقاطع MP4 بدقة فائقة</p>
          </div>
        `;
      }
    });

    // Paste external URL directly
    const addUrlBtn = document.getElementById("addExternalMediaBtn");
    const externalUrlInput = document.getElementById("externalMediaUrl");
    const externalTypeSelect = document.getElementById("externalMediaType");
    if (addUrlBtn && externalUrlInput) {
      addUrlBtn.addEventListener("click", function () {
        const url = externalUrlInput.value.trim();
        if (!url) return;
        mediaList.push({
          url: url,
          media_type: externalTypeSelect ? externalTypeSelect.value : "image",
          caption: "",
        });
        if (!coverImageInput.value) coverImageInput.value = url;
        externalUrlInput.value = "";
        renderMediaPreviews();
      });
    }
  }

  // Tracking Evidence Photo Uploader
  const trackingDropzone = document.getElementById("trackingDropzone");
  const trackingFileInput = document.getElementById("trackingFileInput");
  const trackingMediaJson = document.getElementById("proof_media_json");
  const trackingPreview = document.getElementById("trackingMediaPreview");

  if (trackingDropzone && trackingFileInput && trackingPreview && trackingMediaJson) {
    let proofList = [];
    try {
      proofList = JSON.parse(trackingMediaJson.value || "[]");
    } catch (e) {
      proofList = [];
    }

    function renderProof() {
      trackingPreview.innerHTML = "";
      proofList.forEach((url, i) => {
        const item = document.createElement("div");
        item.className = "relative group border border-gray-700 rounded overflow-hidden";
        item.innerHTML = `
          <img src="${url}" class="w-full h-24 object-cover" />
          <button type="button" class="absolute top-1 right-1 bg-red-600 hover:bg-red-500 text-white p-1 rounded text-xs" data-i="${i}">
            <i class="fas fa-times"></i>
          </button>
        `;
        trackingPreview.appendChild(item);
      });
      trackingMediaJson.value = JSON.stringify(proofList);

      trackingPreview.querySelectorAll("button").forEach((btn) => {
        btn.addEventListener("click", function () {
          const i = parseInt(this.getAttribute("data-i"));
          proofList.splice(i, 1);
          renderProof();
        });
      });
    }

    renderProof();

    trackingDropzone.addEventListener("click", () => trackingFileInput.click());
    trackingFileInput.addEventListener("change", async function () {
      if (this.files.length === 0) return;
      const fd = new FormData();
      for (let i = 0; i < this.files.length; i++) {
        fd.append("files", this.files[i]);
      }
      fd.append("category", "tracking");

      try {
        const res = await fetch("/api/media/upload-multiple", {
          method: "POST",
          body: fd,
        });
        const data = await res.json();
        if (data.success) {
          data.files.forEach((f) => proofList.push(f.url));
          renderProof();
        }
      } catch (err) {
        console.error(err);
      }
    });

    // Support external proof URL
    const addProofUrlBtn = document.getElementById("addProofUrlBtn");
    const proofUrlInput = document.getElementById("proofUrlInput");
    if (addProofUrlBtn && proofUrlInput) {
      addProofUrlBtn.addEventListener("click", function () {
        const val = proofUrlInput.value.trim();
        if (val) {
          proofList.push(val);
          proofUrlInput.value = "";
          renderProof();
        }
      });
    }
  }

  // -------------------------------------------------------------
  // Quick Stock Adjuster (+ / - buttons on vehicles table)
  // -------------------------------------------------------------
  document.querySelectorAll(".stock-adjust-btn").forEach((btn) => {
    btn.addEventListener("click", async function (e) {
      e.preventDefault();
      const vehicleId = this.getAttribute("data-vehicle-id");
      const delta = parseInt(this.getAttribute("data-delta"), 10);
      const displaySpan = document.getElementById(`stock-val-${vehicleId}`);
      const row = this.closest("tr");

      const fd = new FormData();
      fd.append("delta", delta);

      try {
        const res = await fetch(`/admin/vehicles/${vehicleId}/quick-stock`, {
          method: "POST",
          body: fd,
        });
        const data = await res.json();
        if (data.success && displaySpan) {
          displaySpan.textContent = data.units_available;
          displaySpan.className = data.units_available > 0 
            ? "font-bold text-sm text-emerald-400 font-mono" 
            : "font-bold text-sm text-red-400 font-mono";

          // Also update quick-status select if present
          if (row) {
            const statusSelect = row.querySelector(".quick-status-select");
            if (statusSelect && data.status) {
              statusSelect.value = data.status;
            }
          }
        }
      } catch (err) {
        console.error("Failed to update stock:", err);
      }
    });
  });

  // -------------------------------------------------------------
  // Master Dashboard Tab Switcher
  // -------------------------------------------------------------
  const tabButtons = document.querySelectorAll(".dash-tab-btn");
  const tabPanes = document.querySelectorAll(".dash-tab-pane");

  function switchTab(targetTab) {
    if (!targetTab) return;
    tabButtons.forEach((btn) => {
      const isTarget = btn.getAttribute("data-tab") === targetTab;
      if (isTarget) {
        btn.classList.add("bg-gold", "text-black", "font-bold", "shadow-lg");
        btn.classList.remove("text-gray-400", "hover:text-white", "hover:bg-white/5");
      } else {
        btn.classList.remove("bg-gold", "text-black", "font-bold", "shadow-lg");
        btn.classList.add("text-gray-400", "hover:text-white", "hover:bg-white/5");
      }
    });

    tabPanes.forEach((pane) => {
      if (pane.id === `tab-pane-${targetTab}`) {
        pane.classList.remove("hidden");
      } else {
        pane.classList.add("hidden");
      }
    });
  }

  tabButtons.forEach((btn) => {
    btn.addEventListener("click", function () {
      const target = this.getAttribute("data-tab");
      switchTab(target);
      // Update URL without full reload
      const newUrl = new URL(window.location);
      newUrl.searchParams.set("tab", target);
      window.history.replaceState({}, "", newUrl);
    });
  });

  // Check URL query param for default tab
  const urlParams = new URLSearchParams(window.location.search);
  const activeTabParam = urlParams.get("tab") || "vehicles";
  if (document.getElementById(`tab-pane-${activeTabParam}`)) {
    switchTab(activeTabParam);
  }

  // -------------------------------------------------------------
  // Live Vehicle Table Search & Filter on Dashboard
  // -------------------------------------------------------------
  const searchInput = document.getElementById("dashVehicleSearch");
  const filterBtns = document.querySelectorAll(".dash-status-filter-btn");
  let currentFilter = "all";

  function filterVehicleRows() {
    const term = (searchInput ? searchInput.value.toLowerCase().trim() : "");
    const rows = document.querySelectorAll(".dash-vehicle-row");

    rows.forEach((row) => {
      const status = row.getAttribute("data-status");
      const searchData = (row.getAttribute("data-search") || "").toLowerCase();

      const matchesStatus = (currentFilter === "all" || status === currentFilter);
      const matchesSearch = (!term || searchData.includes(term));

      if (matchesStatus && matchesSearch) {
        row.style.display = "";
      } else {
        row.style.display = "none";
      }
    });
  }

  if (searchInput) {
    searchInput.addEventListener("input", filterVehicleRows);
  }

  filterBtns.forEach((btn) => {
    btn.addEventListener("click", function () {
      filterBtns.forEach((b) => {
        b.classList.remove("bg-gold", "text-black", "font-bold");
        b.classList.add("bg-white/5", "text-gray-400");
      });
      this.classList.add("bg-gold", "text-black", "font-bold");
      this.classList.remove("bg-white/5", "text-gray-400");

      currentFilter = this.getAttribute("data-status");
      filterVehicleRows();
    });
  });

  // -------------------------------------------------------------
  // Luxury Preset Photo Quick-Pickers for Vehicle Form
  // -------------------------------------------------------------
  document.querySelectorAll(".preset-photo-btn").forEach((btn) => {
    btn.addEventListener("click", function () {
      const url = this.getAttribute("data-img-url");
      const caption = this.getAttribute("data-caption") || "";
      const mediaJsonInput = document.getElementById("media_json");
      const coverImageInput = document.getElementById("cover_image");

      if (mediaJsonInput && url) {
        let mediaList = [];
        try {
          mediaList = JSON.parse(mediaJsonInput.value || "[]");
        } catch (e) {
          mediaList = [];
        }

        mediaList.push({
          url: url,
          media_type: "image",
          caption: caption,
        });

        if (coverImageInput && !coverImageInput.value) {
          coverImageInput.value = url;
        }

        mediaJsonInput.value = JSON.stringify(mediaList);
        // Dispatch event or call render if function available
        const evt = new CustomEvent("mediaListUpdated");
        window.dispatchEvent(evt);
        location.reload(); // Simple refresh to show new preset photo
      }
    });
  });
});
