// Tab switching functionality
const tabButtons = document.querySelectorAll('.tab-button');
const tabPanes = document.querySelectorAll('.tab-pane');

tabButtons.forEach(button => {
  button.addEventListener('click', () => {
    // Remove active class from all buttons and panes
    tabButtons.forEach(btn => btn.classList.remove('active'));
    tabPanes.forEach(pane => pane.classList.remove('active'));
    
    // Add active class to the clicked button and corresponding pane
    button.classList.add('active');
    document.getElementById(button.getAttribute('data-tab')).classList.add('active');
  });
});

// Toggle password visibility for Scraping Tab
document.getElementById('togglePassword').addEventListener('click', function () {
  const passwordInput = document.getElementById('linkedinPassword');
  const currentType = passwordInput.getAttribute('type');
  const newType = currentType === 'password' ? 'text' : 'password';
  passwordInput.setAttribute('type', newType);
});

// Toggle password visibility for Connection Requests Tab
document.getElementById('togglePasswordConn').addEventListener('click', function () {
  const passwordInput = document.getElementById('connLinkedinPassword');
  const currentType = passwordInput.getAttribute('type');
  const newType = currentType === 'password' ? 'text' : 'password';
  passwordInput.setAttribute('type', newType);
});

// Log form submissions (optional debugging)
document.getElementById('scraperForm').addEventListener('submit', function(e) {
  console.log("Scraping form submitted. Starting scraping process...");
});
document.getElementById('connectionForm').addEventListener('submit', function(e) {
  console.log("Connection form submitted. Starting connection requests process...");
});
