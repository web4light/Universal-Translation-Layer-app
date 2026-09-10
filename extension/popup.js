document.addEventListener('DOMContentLoaded', () => {
  const openBtn = document.getElementById('openSidePanelBtn');
  
  openBtn.addEventListener('click', async () => {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tab && chrome.sidePanel) {
      await chrome.sidePanel.open({ tabId: tab.id });
      window.close();
    }
  });

  const chkAvatar = document.getElementById('chkAvatar');
  chkAvatar.addEventListener('change', async (e) => {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tab) {
      chrome.tabs.sendMessage(tab.id, { action: 'toggle_avatar', enabled: e.target.checked });
    }
  });
});
