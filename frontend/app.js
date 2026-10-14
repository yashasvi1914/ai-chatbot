const sendBtnBottom = document.getElementById('sendBtnBottom');
const userInputBottom = document.getElementById('userInputBottom');
const chatFeed = document.getElementById('chatFeed');
const newChatBtn = document.getElementById('newChatBtn');

function createBubble(text, role) {
  const bubble = document.createElement('div');
  bubble.className = `msg ${role}`;
  if (role === 'bot') {
    bubble.innerHTML = text;
  } else {
    bubble.textContent = text;
  }
  return bubble;
}

function scrollChatDown() {
  if (chatFeed) {
    chatFeed.scrollTop = chatFeed.scrollHeight;
  }
}

async function sendMessage() {
  if (!userInputBottom) return;
  const text = userInputBottom.value.trim();
  if (!text) return;

  const userBubble = createBubble(text, 'user');
  chatFeed.appendChild(userBubble);
  userInputBottom.value = '';
  scrollChatDown();

  const botBubble = createBubble('Thinking...', 'bot');
  botBubble.textContent = 'Thinking...';
  chatFeed.appendChild(botBubble);
  scrollChatDown();

  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text })
    });

    if (!response.ok) {
      throw new Error(`Server returned ${response.status}`);
    }

    const data = await response.json();
    if (data.reply) {
      botBubble.innerHTML = data.reply;
    } else {
      botBubble.textContent = 'No reply from backend.';
    }
  } catch (error) {
    console.error(error);
    botBubble.textContent = 'Error: Could not reach the backend.';
  }

  scrollChatDown();
}

if (sendBtnBottom) {
  sendBtnBottom.addEventListener('click', sendMessage);
}

if (userInputBottom) {
  userInputBottom.addEventListener('keypress', (event) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      sendMessage();
    }
  });
}

function addInitialGreeting() {
  if (!chatFeed) return;
  const greeting = createBubble('Namaste! How can I help you today?', 'bot');
  chatFeed.appendChild(greeting);
}

if (newChatBtn) {
  newChatBtn.addEventListener('click', () => {
    if (chatFeed) chatFeed.innerHTML = '';
    addInitialGreeting();
    if (userInputBottom) userInputBottom.focus();
  });
}

window.addEventListener('DOMContentLoaded', () => {
  addInitialGreeting();
});
