
const statusText = document.getElementById("status");
const messages = document.getElementById("messages");
const chatForm = document.getElementById("chatForm");
const messageInput = document.getElementById("messageInput");
const sendButton = document.getElementById("sendButton");

const groupModeButton = document.getElementById("groupModeButton");
const chatModeStatus = document.getElementById("chatModeStatus");
const selectedRecipientText = document.getElementById("selectedRecipient");
const chatTitle = document.getElementById("chatTitle");
const chatSubtitle = document.getElementById("chatSubtitle");

const userSearchForm = document.getElementById("userSearchForm");
const userSearchInput = document.getElementById("userSearchInput");
const searchUsersButton = document.getElementById("searchUsersButton");
const userSearchResults = document.getElementById("userSearchResults");
const privateConversations = document.getElementById("privateConversations");


const messengerLayout = document.querySelector(".messenger-layout");
const toggleSidebarButton = document.getElementById("toggleSidebarButton");
const sidebarBackdrop = document.getElementById("sidebarBackdrop");

function setSidebarOpen(isOpen) {
    if (window.innerWidth > 760) return;

    messengerLayout.classList.toggle("sidebar-open", isOpen);
    toggleSidebarButton.setAttribute("aria-expanded", String(isOpen));
}

toggleSidebarButton.addEventListener("click", () => {
    const isOpen = messengerLayout.classList.contains("sidebar-open");
    setSidebarOpen(!isOpen);
});

sidebarBackdrop.addEventListener("click", () => {
    setSidebarOpen(false);
});

document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
        setSidebarOpen(false);
    }
});

window.addEventListener("resize", () => {
    if (window.innerWidth > 760) {
        messengerLayout.classList.remove("sidebar-open");
        toggleSidebarButton.setAttribute("aria-expanded", "false");
    }
});


let socket = null;
let currentUsername = "";
let currentChat = "group";

// پیام‌های هر گفتگو در حافظه مرورگر
const conversations = new Map();

conversations.set("group", {
    type: "group",
    username: "چت عمومی",
    messages: []
});


// ساخت شناسه برای گفتگوی خصوصی
function privateChatId(username) {
    return `private:${username.toLowerCase()}`;
}


// ایجاد گفتگو در صورت نبودن آن

function ensurePrivateConversation(username) {
    const id = privateChatId(username);

    if (!conversations.has(id)) {
        conversations.set(id, {
            type: "private",
            username: username,
            messages: [],
            loaded: false
        });

        renderConversationList();
    }

    return conversations.get(id);
}



// ساخت حباب پیام
// ساخت حباب پیام
function createMessageElement(message, chatId) {
    const item = document.createElement("div");

    item.className = "message";

    const isOwnMessage = message.sender === currentUsername;
    const isPrivateChat = chatId.startsWith("private:");

    if (isOwnMessage) {
        item.classList.add("message-own");
    } else {
        item.classList.add("message-other");
    }

    const sender = document.createElement("strong");
    sender.textContent = message.sender;

    const content = document.createElement("span");
    content.textContent = message.text;

    item.append(sender, content);

    // نمایش تیک برای پیام‌های خصوصی خودمان
    if (isOwnMessage && isPrivateChat && message.id !== null) {
        const status = document.createElement("span");
        status.className = "message-status";
        status.textContent = message.isRead ? "✓✓" : "✓";
        status.title = message.isRead
            ? "خوانده شده"
            : "ارسال شده";

        item.appendChild(status);
    }

    return item;
}


// نمایش پیام‌های گفتگوی انتخاب‌شده
function renderMessages() {
    const conversation = conversations.get(currentChat);

    messages.replaceChildren();

    if (!conversation) {
        return;
    }

    conversation.messages.forEach((message) => {
        messages.appendChild(createMessageElement(message, currentChat));
    });

    messages.scrollTop = messages.scrollHeight;
}


// اضافه کردن پیام به گفتگوی مناسب
// اضافه کردن پیام به گفتگوی مناسب
function addMessage(
    chatId,
    sender,
    text,
    id = null,
    isRead = false
) {
    


    const conversation = conversations.get(chatId);

    if (!conversation) {
        return;
    }

    conversation.messages.push({
        id: id,
        sender: sender,
        text: text,
        isRead: isRead
    });

    if (chatId.startsWith("private:")) {
        renderConversationList();
    }

    if (currentChat === chatId) {
        renderMessages();
    }
}

async function loadPrivateHistory(username) {
    const chatId = privateChatId(username);
    const conversation = conversations.get(chatId);

    if (!conversation || conversation.loaded) {
        return;
    }

    try {
        const response = await fetch(
            `/api/messages?username=${encodeURIComponent(username)}`
        );

        if (!response.ok) {
            statusText.textContent =
                "دریافت تاریخچه پیام‌ها ناموفق بود.";
            return;
        }

        const data = await response.json();

        conversation.messages = data.messages.map((item) => ({
            id: item.id,
            sender: item.sender,
            text: item.message,
            isRead: item.is_read
        }));

        conversation.loaded = true;

        renderConversationList();

        if (currentChat === chatId) {
            renderMessages();
        }
    } catch (error) {
        statusText.textContent =
            "خطا در دریافت تاریخچه پیام‌ها.";
        console.error(error);
    }
}

// ساخت فهرست گفتگوهای خصوصی
function renderConversationList() {
    privateConversations.replaceChildren();

    for (const [id, conversation] of conversations) {
        if (conversation.type !== "private") {
            continue;
        }

        const button = document.createElement("button");
        button.type = "button";
        button.className = "conversation-item";

        if (currentChat === id) {
            button.classList.add("active");
        }

        const avatar = document.createElement("span");
        avatar.className = "conversation-avatar";
        avatar.textContent = conversation.username.slice(0, 2);

        const details = document.createElement("span");
        details.className = "conversation-details";

        const name = document.createElement("strong");
        name.textContent = conversation.username;

        const preview = document.createElement("small");
        const lastMessage =
            conversation.messages[conversation.messages.length - 1];

        preview.textContent = lastMessage
            ? lastMessage.text
            : "شروع گفتگو";

        details.append(name, preview);
        button.append(avatar, details);

        button.addEventListener("click", () => {
            openConversation(id);
        });

        privateConversations.appendChild(button);
    }

    if (currentChat === "group") {
        groupModeButton.classList.add("active");
    } else {
        groupModeButton.classList.remove("active");
    }
}


// باز کردن گفتگوی انتخاب‌شده
function openConversation(id) {
    if (!conversations.has(id)) {
        return;
    }

    currentChat = id;

    setSidebarOpen(false);

    const conversation = conversations.get(id);

    if (conversation.type === "group") {
        chatTitle.textContent = "چت عمومی";
        chatSubtitle.textContent = "گفتگو با کاربران پیام‌رسان";
        chatModeStatus.textContent = "عمومی";
        messageInput.placeholder = "پیام عمومی بنویس...";
        selectedRecipientText.textContent =
            "گیرنده‌ای انتخاب نشده است.";
    } else {
        chatTitle.textContent = conversation.username;
        chatSubtitle.textContent = "گفتگوی خصوصی";
        chatModeStatus.textContent = "خصوصی";
        messageInput.placeholder =
            `پیام خصوصی برای ${conversation.username}...`;
        selectedRecipientText.textContent =
            `گیرنده: ${conversation.username}`;
    }

renderMessages();
renderConversationList();


if (conversation.type === "private") {
    loadPrivateHistory(conversation.username);
}

// اگر گفتگوی خصوصی باز شده، خوانده‌شدن پیام‌ها را اعلام کن
if (conversation.type === "private" && socket?.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({
        type: "mark_read",
        sender: conversation.username
    }));
}

if (window.innerWidth > 760) {
    messageInput.focus();
}
}


// انتخاب چت عمومی
groupModeButton.addEventListener("click", () => {
    openConversation("group");
});


// جست‌وجوی کاربران
userSearchForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const query = userSearchInput.value.trim();

    if (!query) {
        userSearchResults.textContent = "نام کاربری را وارد کن.";
        return;
    }

    searchUsersButton.disabled = true;
    userSearchResults.textContent = "در حال جست‌وجو...";

    try {
        const response = await fetch(
            `/api/users/search?q=${encodeURIComponent(query)}`
        );

        if (!response.ok) {
            userSearchResults.textContent =
                response.status === 401
                    ? "نشست ورود معتبر نیست؛ دوباره وارد شو."
                    : "جست‌وجو ناموفق بود.";
            return;
        }

        const data = await response.json();
        userSearchResults.replaceChildren();

        if (!data.users.length) {
            userSearchResults.textContent = "کاربری پیدا نشد.";
            return;
        }

        data.users.forEach((user) => {
            const button = document.createElement("button");
            button.type = "button";
            button.textContent = user.username;

            button.addEventListener("click", () => {
                ensurePrivateConversation(user.username);
                openConversation(privateChatId(user.username));

                userSearchResults.replaceChildren();
                userSearchInput.value = "";
            });

            userSearchResults.appendChild(button);
        });
    } catch {
        userSearchResults.textContent =
            "ارتباط با سرور برقرار نشد.";
    } finally {
        searchUsersButton.disabled = false;
    }
});


// اتصال به سرور
function connectToChat() {
    const protocol =
        window.location.protocol === "https:" ? "wss:" : "ws:";

    socket = new WebSocket(
        `${protocol}//${window.location.host}/ws`
    );

    socket.addEventListener("open", () => {
        statusText.textContent = "اتصال برقرار شد؛ در حال بررسی حساب...";
    });

    socket.addEventListener("message", (event) => {
        let data;

        try {
            data = JSON.parse(event.data);
        } catch {
            return;
        }

        if (data.type === "login_success") {
            currentUsername = data.username;

            statusText.textContent =
                `متصل شدی؛ خوش آمدی ${currentUsername}`;

            messageInput.disabled = false;
            sendButton.disabled = false;
            groupModeButton.disabled = false;
            userSearchInput.disabled = false;
            searchUsersButton.disabled = false;

            renderMessages();
            return;
        }

        // پیام عمومی
        if (data.type === "group_message") {
            addMessage("group", data.username, data.message);
            return;
        }

        // پیام خصوصی دریافتی یا پیام آفلاین
        if (data.type === "private_message") {
            const conversation = ensurePrivateConversation(data.username);

            const chatId = privateChatId(conversation.username);

            addMessage(
                chatId,
                data.username,
                data.message,
                data.id,
                false
            );

            // اگر همین گفتگو باز است، پیام دریافتی را خوانده‌شده اعلام کن
            if (currentChat === chatId && socket?.readyState === WebSocket.OPEN) {
                socket.send(JSON.stringify({
                    type: "mark_read",
                    sender: data.username
                }));
            }

            return;
        }

        // تأیید ارسال پیام خصوصی
        if (data.type === "private_message_sent") {
            const conversation = ensurePrivateConversation(data.recipient);

            addMessage(
                privateChatId(conversation.username),
                currentUsername,
                data.message,
                data.id,
                false
            );

            return;
        }
        
                // به‌روزرسانی وضعیت پیام‌های خوانده‌شده
       // به‌روزرسانی وضعیت پیام‌های خوانده‌شده
if (data.type === "messages_read") {
    const chatId = privateChatId(data.reader);
    const conversation = conversations.get(chatId);

    if (
        conversation &&
        Array.isArray(data.message_ids)
    ) {
        const readIds = new Set(data.message_ids);

        conversation.messages.forEach((message) => {
            if (readIds.has(message.id)) {
                message.isRead = true;
            }
        });

        if (currentChat === chatId) {
            renderMessages();
        }
    }

    return;
}

        if (data.type === "private_message_error") {
            statusText.textContent = data.message;
        }
    });

    socket.addEventListener("close", () => {
        statusText.textContent =
            "اتصال قطع شد؛ دوباره وارد حساب شو.";

        messageInput.disabled = true;
        sendButton.disabled = true;
        groupModeButton.disabled = true;
        userSearchInput.disabled = true;
        searchUsersButton.disabled = true;
    });

    socket.addEventListener("error", () => {
        statusText.textContent = "خطا در ارتباط با سرور.";
    });
}


// ارسال پیام در گفتگوی فعلی
chatForm.addEventListener("submit", (event) => {
    event.preventDefault();

    const text = messageInput.value.trim();

    if (!text) {
        return;
    }

    if (!socket || socket.readyState !== WebSocket.OPEN) {
        statusText.textContent = "اتصال برقرار نیست.";
        return;
    }

    if (currentChat === "group") {
        socket.send(JSON.stringify({
            type: "group_message",
            message: text
        }));
    } else {
        const conversation = conversations.get(currentChat);

        if (!conversation) {
            return;
        }

        socket.send(JSON.stringify({
            type: "private_message",
            recipient: conversation.username,
            message: text
        }));
    }

    messageInput.value = "";
    messageInput.focus();
});


// شروع برنامه
renderConversationList();
renderMessages();
connectToChat();
