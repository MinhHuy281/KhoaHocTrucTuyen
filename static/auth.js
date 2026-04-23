document.addEventListener("DOMContentLoaded", function () {
    const toggleButtons = document.querySelectorAll(".password-toggle");
    const authForms = document.querySelectorAll(".auth-form");
    const phoneInputs = document.querySelectorAll('input[name="phone"]');

    const allowControlKey = (event) => {
        return (
            event.ctrlKey ||
            event.metaKey ||
            [
                "Backspace",
                "Delete",
                "Tab",
                "Enter",
                "ArrowLeft",
                "ArrowRight",
                "ArrowUp",
                "ArrowDown",
                "Home",
                "End",
            ].includes(event.key)
        );
    };

    const attachPhoneInputFilter = (input) => {
        if (!input || input.dataset.phoneFilterAttached === "1") {
            return;
        }

        input.dataset.phoneFilterAttached = "1";

        input.addEventListener("keydown", function (event) {
            if (allowControlKey(event)) {
                return;
            }

            if (!/^\d$/.test(event.key)) {
                event.preventDefault();
            }
        });

        input.addEventListener("beforeinput", function (event) {
            if (!event.data) {
                return;
            }

            if (!/^\d+$/.test(event.data)) {
                event.preventDefault();
            }
        });

        input.addEventListener("paste", function (event) {
            event.preventDefault();

            const pastedText = (event.clipboardData || window.clipboardData).getData("text");
            const numbersOnly = pastedText.replace(/\D/g, "");

            if (!numbersOnly) {
                return;
            }

            const start = this.selectionStart ?? this.value.length;
            const end = this.selectionEnd ?? this.value.length;
            const nextValue = this.value.slice(0, start) + numbersOnly + this.value.slice(end);

            this.value = nextValue;
            const cursorPos = start + numbersOnly.length;
            this.setSelectionRange(cursorPos, cursorPos);
            this.dispatchEvent(new Event("input", { bubbles: true }));
        });
    };

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

    phoneInputs.forEach((input) => {
        attachPhoneInputFilter(input);
    });
});
