// MOTORA Client-side Javascript

document.addEventListener("DOMContentLoaded", function () {
  // Mobile Menu Toggle
  const mobileMenuBtn = document.getElementById("mobile-menu-btn");
  const mobileMenu = document.getElementById("mobile-menu");
  if (mobileMenuBtn && mobileMenu) {
    mobileMenuBtn.addEventListener("click", function () {
      mobileMenu.classList.toggle("hidden");
    });
  }

  // Reservation Modal Logic
  const reserveModal = document.getElementById("reserveModal");
  const openModalBtns = document.querySelectorAll(".btn-open-reserve");
  const closeModalBtn = document.getElementById("closeReserveModal");
  const reserveForm = document.getElementById("reserveForm");

  if (reserveModal) {
    openModalBtns.forEach((btn) => {
      btn.addEventListener("click", function () {
        const vehicleId = this.getAttribute("data-vehicle-id");
        const vehicleTitle = this.getAttribute("data-vehicle-title");
        const vehiclePrice = this.getAttribute("data-vehicle-price");
        const vehicleDeposit = this.getAttribute("data-vehicle-deposit");

        if (document.getElementById("modal_vehicle_id")) {
          document.getElementById("modal_vehicle_id").value = vehicleId;
        }
        if (document.getElementById("modal_vehicle_title")) {
          document.getElementById("modal_vehicle_title").textContent = vehicleTitle;
        }
        if (document.getElementById("modal_vehicle_price")) {
          document.getElementById("modal_vehicle_price").textContent = vehiclePrice;
        }
        if (document.getElementById("modal_vehicle_deposit")) {
          document.getElementById("modal_vehicle_deposit").textContent = vehicleDeposit;
        }

        // Reset response message state
        const statusMsg = document.getElementById("modalStatusMsg");
        if (statusMsg) statusMsg.classList.add("hidden");
        if (reserveForm) {
          reserveForm.classList.remove("hidden");
          reserveForm.reset();
        }

        reserveModal.classList.remove("hidden");
        reserveModal.classList.add("flex");
      });
    });

    if (closeModalBtn) {
      closeModalBtn.addEventListener("click", function () {
        reserveModal.classList.add("hidden");
        reserveModal.classList.remove("flex");
      });
    }

    reserveModal.addEventListener("click", function (e) {
      if (e.target === reserveModal) {
        reserveModal.classList.add("hidden");
        reserveModal.classList.remove("flex");
      }
    });

    // Form Submission
    if (reserveForm) {
      reserveForm.addEventListener("submit", async function (e) {
        e.preventDefault();
        const submitBtn = document.getElementById("reserveSubmitBtn");
        const originalText = submitBtn ? submitBtn.innerHTML : "";
        if (submitBtn) {
          submitBtn.disabled = true;
          submitBtn.innerHTML = "<span>جاري تأكيد الطلب... / Submitting...</span>";
        }

        const formData = new FormData(reserveForm);
        try {
          const res = await fetch("/api/reserve", {
            method: "POST",
            body: formData,
          });
          const data = await res.json();

          if (data.success) {
            reserveForm.classList.add("hidden");
            const statusBox = document.getElementById("modalStatusMsg");
            const codeSpan = document.getElementById("confirmedBookingCode");
            const trackingLink = document.getElementById("modalTrackingLink");

            if (codeSpan) codeSpan.textContent = data.booking_code;
            if (trackingLink) trackingLink.href = data.tracking_url;
            if (statusBox) statusBox.classList.remove("hidden");
          } else {
            alert(data.message || "حدث خطأ أثناء إرسال الحجز، يرجى المحاولة ثانية.");
          }
        } catch (err) {
          console.error(err);
          alert("تعذر الاتصال بالخادم، يرجى التحقق من اتصال الإنترنت.");
        } finally {
          if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText;
          }
        }
      });
    }
  }

  // Lightbox Media Viewer
  const lightbox = document.getElementById("lightboxModal");
  const lightboxImg = document.getElementById("lightboxImage");
  const lightboxCaption = document.getElementById("lightboxCaption");
  const lightboxClose = document.getElementById("lightboxClose");

  if (lightbox) {
    document.querySelectorAll(".open-lightbox").forEach((el) => {
      el.addEventListener("click", function (e) {
        e.preventDefault();
        const imgUrl = this.getAttribute("data-full-img") || this.src || this.href;
        const caption = this.getAttribute("data-caption") || "";

        if (lightboxImg) lightboxImg.src = imgUrl;
        if (lightboxCaption) lightboxCaption.textContent = caption;
        lightbox.classList.remove("hidden");
        lightbox.classList.add("flex");
      });
    });

    if (lightboxClose) {
      lightboxClose.addEventListener("click", function () {
        lightbox.classList.add("hidden");
        lightbox.classList.remove("flex");
      });
    }

    lightbox.addEventListener("click", function (e) {
      if (e.target === lightbox) {
        lightbox.classList.add("hidden");
        lightbox.classList.remove("flex");
      }
    });
  }

  // Details Page Gallery Thumbnail Swapper
  const mainGalleryImg = document.getElementById("mainGalleryImage");
  const thumbs = document.querySelectorAll(".gallery-thumbnail");
  if (mainGalleryImg && thumbs.length > 0) {
    thumbs.forEach((t) => {
      t.addEventListener("click", function () {
        const fullSrc = this.getAttribute("data-full");
        if (fullSrc) {
          mainGalleryImg.src = fullSrc;
          thumbs.forEach((x) => x.classList.remove("border-gold"));
          this.classList.add("border-gold");
        }
      });
    });
  }
});
