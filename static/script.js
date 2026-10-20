
// گرفتن عناصر
const usernameInput = document.getElementById("username");
const passwordInput = document.getElementById("password");
const connectButton = document.getElementById("connectButton");
const statusText = document.getElementById("status");
const messages = document.getElementById("messages");
const chatForm = document.getElementById("chatForm");
const messageInput = document.getElementById("messageInput");
const sendButton = document.getElementById("sendButton");

// متغیر اتصال
let socket = null;

//وقتی کاربر روی دکمه اتصال کلیک می‌کند
connectButton.addEventListener("click", () => {
    const username = usernameInput.value.trim();
    const password = passwordInput.value.trim();

    if (!username) {
        statusText.textContent = "ابتدا نام کاربری را وارد کن.";
        return;
    }

    if (!password) {
        statusText.textContent = "رمز عبور را وارد کن.";
        return;
    }
    //بررسی اتصال قبلی
    if (socket && socket.readyState !== WebSocket.CLOSED) {
        statusText.textContent = "اتصال قبلی هنوز برقرار است.";
        return;
    }
    //ساخت اتصال WebSocket
    const protocol =
        window.location.protocol === "https:" ? "wss:" : "ws:";

    socket = new WebSocket(
        `${protocol}//${window.location.host}/ws`
    );

    socket.addEventListener("open", () => {
        socket.send(JSON.stringify({
            username: username,
            password: password
        }));

        statusText.textContent = "در حال بررسی رمز عبور...";

        usernameInput.disabled = true;
        passwordInput.disabled = true;
        connectButton.disabled = true;
    });
    //دریافت پیام از سرور
    socket.addEventListener("message", (event) => {
        const data = JSON.parse(event.data);

        if (data.type === "login_success") {
            statusText.textContent = "ورود موفق بود.";
            messageInput.disabled = false;
            sendButton.disabled = false;
            messageInput.focus();
            return;
        }
        //
        const item = document.createElement("div");
        item.className = "message";

        const sender = document.createElement("strong");
        sender.textContent = data.username + ": ";

        const content = document.createElement("span");
        content.textContent = data.message;

        item.append(sender, content);
        messages.appendChild(item);

        messages.scrollTop = messages.scrollHeight;
    });
    //وقتی اتصال قطع می‌شود
    socket.addEventListener("close", () => {
        statusText.textContent = "اتصال قطع شد.";

        usernameInput.disabled = false;
        passwordInput.disabled = false;
        connectButton.disabled = false;

        messageInput.disabled = true;
        sendButton.disabled = true;
    });
    //وقتی خطای ارتباطی رخ می‌دهد
    socket.addEventListener("error", () => {
        statusText.textContent = "خطا در ارتباط با سرور.";
    });
});
//ارسال پیام چت
chatForm.addEventListener("submit", (event) => {
    event.preventDefault();

    const message = messageInput.value.trim();
    //وضعیت اتصال بررسی می‌شه
    if (!socket || socket.readyState !== WebSocket.OPEN) {
        statusText.textContent = "ابتدا به سرور متصل شو.";
        return;
    }

    if (!message) return;

    socket.send(JSON.stringify({ message }));

    messageInput.value = "";
    messageInput.focus();
});
