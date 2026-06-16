const packagePriceKeys = {
    Exterior_package: "exterior_price",
    Interior_package: "interior_price",
    Both_package: "both",
};

function money(value) {
    return `$${Number(value || 0).toLocaleString()}`;
}

function getChecked(form, name) {
    return form.querySelector(`[name="${name}"]:checked`);
}

function setupNavigation() {
    const toggle = document.querySelector(".nav-toggle");
    const menu = document.querySelector("#site-menu");
    if (!toggle || !menu) return;

    toggle.addEventListener("click", () => {
        const isOpen = menu.classList.toggle("is-open");
        toggle.setAttribute("aria-expanded", String(isOpen));
    });

    menu.addEventListener("click", (event) => {
        if (event.target.closest("a")) {
            menu.classList.remove("is-open");
            toggle.setAttribute("aria-expanded", "false");
        }
    });
}

function setupReveals() {
    const revealItems = document.querySelectorAll(".reveal");
    if (!revealItems.length) return;

    if (!("IntersectionObserver" in window)) {
        revealItems.forEach((item) => item.classList.add("is-visible"));
        return;
    }

    const observer = new IntersectionObserver(
        (entries) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    entry.target.classList.add("is-visible");
                    observer.unobserve(entry.target);
                }
            });
        },
        { threshold: 0.12 }
    );

    revealItems.forEach((item) => observer.observe(item));
}

function setMinimumBookingDate(form) {
    const dateInput = form.querySelector("#day");
    if (!dateInput) return;

    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    const yyyy = tomorrow.getFullYear();
    const mm = String(tomorrow.getMonth() + 1).padStart(2, "0");
    const dd = String(tomorrow.getDate()).padStart(2, "0");
    dateInput.min = `${yyyy}-${mm}-${dd}`;
}

function readPriceTable() {
    const priceNode = document.querySelector("#price-data");
    if (!priceNode) return {};

    try {
        return JSON.parse(priceNode.textContent);
    } catch {
        return {};
    }
}

function setupBookingSummary() {
    const form = document.querySelector("#booking-form");
    if (!form) return;

    const prices = readPriceTable();
    const summaryVehicle = document.querySelector("#summary-vehicle");
    const summaryPackage = document.querySelector("#summary-package");
    const summaryAddons = document.querySelector("#summary-addons");
    const summaryLines = document.querySelector("#summary-lines");
    const summaryTotal = document.querySelector("#summary-total");

    setMinimumBookingDate(form);

    function selectedVehiclePrices() {
        const vehicle = getChecked(form, "model");
        return prices[vehicle?.value] || prices.Sedan || {};
    }

    function labelFor(input) {
        const card = input?.closest("label");
        const label = card?.querySelector("strong") || card?.querySelector("span");
        return label ? label.textContent.trim() : "";
    }

    function renderPackagePrices() {
        const vehiclePrices = selectedVehiclePrices();
        form.querySelectorAll("[data-package-price]").forEach((node) => {
            const packageValue = node.dataset.packagePrice;
            const key = packagePriceKeys[packageValue];
            node.textContent = money(vehiclePrices[key]);
        });

        form.querySelectorAll("[data-addon-price]").forEach((node) => {
            node.textContent = `+${money(vehiclePrices[node.dataset.addonPrice])}`;
        });
    }

    function renderSummary() {
        const vehicle = getChecked(form, "model");
        const packageInput = getChecked(form, "package");
        const vehiclePrices = selectedVehiclePrices();
        const packageKey = packagePriceKeys[packageInput?.value] || "both";
        const packageTotal = Number(vehiclePrices[packageKey] || 0);
        const checkedAddons = [...form.querySelectorAll('[name="addons[]"]:checked')];

        let total = packageTotal;
        const addonRows = checkedAddons.map((addon) => {
            const price = Number(vehiclePrices[addon.dataset.priceKey] || 0);
            total += price;
            return { name: labelFor(addon), price };
        });

        if (summaryVehicle) summaryVehicle.textContent = labelFor(vehicle) || "Sedan";
        if (summaryPackage) summaryPackage.textContent = labelFor(packageInput) || "Detail";
        if (summaryAddons) summaryAddons.textContent = addonRows.length ? addonRows.map((row) => row.name).join(", ") : "None";

        if (summaryLines) {
            const rows = [
                `<div class="summary-line"><span>Package</span><strong>${money(packageTotal)}</strong></div>`,
                ...addonRows.map((row) => `<div class="summary-line"><span>${row.name}</span><strong>${money(row.price)}</strong></div>`),
            ];
            summaryLines.innerHTML = rows.join("");
        }

        if (summaryTotal) summaryTotal.textContent = money(total);
    }

    function refresh() {
        renderPackagePrices();
        renderSummary();
    }

    form.addEventListener("change", refresh);
    refresh();
}

document.addEventListener("DOMContentLoaded", () => {
    setupNavigation();
    setupReveals();
    setupBookingSummary();
});
