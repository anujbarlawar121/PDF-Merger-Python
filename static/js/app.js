const body = document.body;
const tabButtons = Array.from(document.querySelectorAll("[data-tab-target]"));
const tabPanels = Array.from(document.querySelectorAll("[data-tool-panel]"));

function activateTool(toolName) {
    tabButtons.forEach((button) => {
        const isActive = button.dataset.tabTarget === toolName;
        button.classList.toggle("is-active", isActive);
        button.setAttribute("aria-selected", String(isActive));
    });

    tabPanels.forEach((panel) => {
        const isActive = panel.dataset.toolPanel === toolName;
        panel.classList.toggle("is-active", isActive);
    });
}

tabButtons.forEach((button) => {
    button.addEventListener("click", () => {
        const { tabTarget } = button.dataset;
        activateTool(tabTarget);
        history.replaceState(null, "", `?tool=${tabTarget}#toolkit`);
    });
});

document.querySelectorAll("[data-file-picker]").forEach((picker) => {
    const input = picker.querySelector("input[type='file']");
    const summary = picker.querySelector("[data-file-summary]");

    const updateSummary = () => {
        const files = Array.from(input.files || []);
        if (!files.length) {
            summary.textContent = input.multiple ? "No files selected yet." : "No file selected yet.";
            return;
        }

        summary.textContent = files.map((file) => file.name).join(", ");
    };

    input.addEventListener("change", updateSummary);
});

document.querySelectorAll(".tool-form").forEach((form) => {
    form.addEventListener("submit", () => {
        const button = form.querySelector(".submit-button");
        if (!button) {
            return;
        }

        button.dataset.originalLabel = button.textContent;
        button.textContent = button.dataset.loadingLabel || "Working...";
        button.disabled = true;
        button.classList.add("is-loading");
    });
});

const initialTool = body.dataset.activeTool || "merge";
const hasInitialPanel = tabPanels.some((panel) => panel.dataset.toolPanel === initialTool);
activateTool(hasInitialPanel ? initialTool : "merge");
