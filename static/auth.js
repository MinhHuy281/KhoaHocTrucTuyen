document.addEventListener("DOMContentLoaded", function () {
    const toggleButtons = document.querySelectorAll(".password-toggle");
    const authForms = document.querySelectorAll(".auth-form");

    toggleButtons.forEach((button) => {
        button.addEventListener("click", function () {
            const targetId = this.getAttribute("data-target");
            const input = document.getElementById(targetId);

            if (!input) {
                return;
            }

            const isHidden = input.type === "password";
            input.type = isHidden ? "text" : "password";

            const icon = this.querySelector("i");
            if (icon) {
                icon.classList.toggle("bi-eye", !isHidden);
                icon.classList.toggle("bi-eye-slash", isHidden);
            }

            this.setAttribute("aria-label", isHidden ? "Ẩn mật khẩu" : "Hiện mật khẩu");
        });
    });

    authForms.forEach((form) => {
        form.addEventListener("submit", function () {
            const submitButtons = this.querySelectorAll("button[type='submit']");
            submitButtons.forEach((btn) => {
                btn.disabled = true;
                btn.style.opacity = "0.75";
                btn.style.cursor = "not-allowed";
            });
        });
    });
});
