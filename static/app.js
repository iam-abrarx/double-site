let currentMode = 'login'; // 'login' or 'register'

const tabLogin = document.getElementById('tab-login');
const tabRegister = document.getElementById('tab-register');
const submitBtn = document.getElementById('submitBtn');
const authForm = document.getElementById('authForm');
const statusMessage = document.getElementById('statusMessage');
const otpSection = document.getElementById('otpSection');
const requestOtpBtn = document.getElementById('requestOtpBtn');

const usernameInput = document.getElementById('username');
const passwordInput = document.getElementById('password');

const verifyForm = document.getElementById('verifyForm');
const otpCodeInput = document.getElementById('otpCode');

function showStatus(text, type) {
    statusMessage.textContent = text;
    statusMessage.className = `status-msg ${type}`;
    statusMessage.classList.remove('hidden');
}

function clearStatus() {
    statusMessage.textContent = '';
    statusMessage.className = 'status-msg hidden';
}

tabLogin.addEventListener('click', () => {
    currentMode = 'login';
    tabLogin.classList.add('active');
    tabRegister.classList.remove('active');
    submitBtn.textContent = 'Sign In';
    otpSection.classList.add('hidden');
    verifyForm.classList.add('hidden');
    otpCodeInput.value = '';
    clearStatus();
    const emailOtpContainer = document.getElementById('emailOtpContainer');
    if (emailOtpContainer) emailOtpContainer.classList.remove('hidden');
});

tabRegister.addEventListener('click', () => {
    currentMode = 'register';
    tabRegister.classList.add('active');
    tabLogin.classList.remove('active');
    submitBtn.textContent = 'Register';
    otpSection.classList.add('hidden');
    verifyForm.classList.add('hidden');
    otpCodeInput.value = '';
    clearStatus();
    const emailOtpContainer = document.getElementById('emailOtpContainer');
    if (emailOtpContainer) emailOtpContainer.classList.add('hidden');
});

authForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearStatus();

    const username = usernameInput.value.trim();
    const password = passwordInput.value;

    const endpoint = currentMode === 'login' ? '/login' : '/register';

    try {
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, password })
        });

        const data = await response.json();

        if (response.ok) {
            if (currentMode === 'register') {
                showStatus('Registration successful! Please login.', 'success');
                // Switch view to login
                setTimeout(() => tabLogin.click(), 1000);
            } else {
                showStatus('Login successful!', 'success');
                otpSection.classList.remove('hidden');
            }
        } else {
            showStatus(data.error || 'Authentication failed', 'error');
        }
    } catch (error) {
        showStatus('Connection error. Is the server running?', 'error');
    }
});

requestOtpBtn.addEventListener('click', async () => {
    const username = usernameInput.value.trim();
    clearStatus();

    try {
        const response = await fetch('/request-otp', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username })
        });

        const data = await response.json();

        if (response.ok) {
            verifyForm.classList.remove('hidden');
            if (data.sent_telegram) {
                showStatus('OTP has been sent to your Telegram Bot!', 'success');
            } else {
                showStatus('OTP request processed. Please check server console logs (Telegram bot parameters not fully configured).', 'success');
            }
        } else {
            showStatus(data.error || 'Failed to request OTP', 'error');
        }
    } catch (error) {
        showStatus('Connection error. Is the server running?', 'error');
    }
});

verifyForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = usernameInput.value.trim();
    const otp = otpCodeInput.value.trim();
    clearStatus();

    if (otp.length !== 6) {
        showStatus('Please enter a 6-digit verification code.', 'error');
        return;
    }

    try {
        const response = await fetch('/verify-otp', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, otp })
        });

        const data = await response.json();

        if (response.ok) {
            // Transition to Login Success Dashboard View
            document.querySelector('.card').innerHTML = `
                <div style="text-align: center; padding: 1rem 0; animation: slideIn 0.4s ease forwards;">
                    <div style="font-size: 4.5rem; margin-bottom: 1rem; filter: drop-shadow(0 0 15px rgba(16, 185, 129, 0.4));">🔓</div>
                    <h2 style="font-size: 1.8rem; margin-bottom: 0.5rem; color: #fff; font-weight: 700;">Access Granted</h2>
                    <p style="color: var(--text-secondary); margin-bottom: 2rem; font-size: 0.95rem;">You have successfully passed the OTP security gate.</p>
                    <div class="status-msg success" style="margin: 0; font-weight: 600; margin-bottom: 1rem;">Welcome, ${username}!</div>
                    <p style="color: var(--text-secondary); font-size: 0.85rem; animation: pulse 1s infinite;">Redirecting to secure area...</p>
                </div>
            `;
            // Redirect after 1.5 seconds
            setTimeout(() => {
                window.location.href = '/dashboard';
            }, 1800);
        } else {
            showStatus(data.error || 'Verification failed', 'error');
        }
    } catch (error) {
        showStatus('Connection error. Is the server running?', 'error');
    }
});

const emailOtpLink = document.getElementById('emailOtpLink');
if (emailOtpLink) {
    emailOtpLink.addEventListener('click', async (e) => {
        e.preventDefault();
        const username = usernameInput.value.trim();
        const password = passwordInput.value;
        
        if (!username || !password) {
            showStatus('Please enter username and password first.', 'error');
            return;
        }
        
        const email = prompt("Enter your email address to receive OTP:");
        if (!email) return;
        
        clearStatus();
        
        try {
            const response = await fetch('/prefer-email', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password, email })
            });
            const data = await response.json();
            if (response.ok) {
                showStatus('Email preference notified successfully!', 'success');
            } else {
                showStatus(data.error || 'Failed to send email preference', 'error');
            }
        } catch (err) {
            showStatus('Connection error. Is the server running?', 'error');
        }
    });
}
