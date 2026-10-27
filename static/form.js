document.addEventListener("DOMContentLoaded", () => {
  // Force uppercase for certain fields
  const toUpperIds = ["name", "business_name"];
  toUpperIds.forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener("input", () => {
        el.value = el.value.toUpperCase();
      });
    }
  });

  // Password check (Vendor & Customer forms)
  const forms = [
    { formId: "vendorRegisterForm", passId: "vendor_password", confirmId: "vendor_confirm" },
    { formId: "customerRegisterForm", passId: "cust_password", confirmId: "cust_confirm" }
  ];

  forms.forEach(({ formId, passId, confirmId }) => {
    const form = document.getElementById(formId);
    if (form) {
      form.addEventListener("submit", (e) => {
        const p = document.getElementById(passId).value;
        const c = document.getElementById(confirmId).value;
        if (p !== c) {
          e.preventDefault();
          alert("Passwords do not match!");
        }
      });
    }
  });
});
