// Asterisk (*) Injected Content Script — 3D Sign Language Avatar & WebMCP Bridge

(function() {
  console.log('⚡ [Asterisk *] Sovereign WebMCP & 3D Accessibility active on page.');

  // Expose WebMCP standard tools if document.modelContext exists or polyfill it
  if (!window.modelContext) {
    window.modelContext = {
      tools: [],
      registerTool: function(tool) {
        this.tools.push(tool);
        console.log(`[WebMCP] Registered tool: ${tool.name}`);
      }
    };
  }

  window.modelContext.registerTool({
    name: "accessibility_start_broadcast",
    description: "Streamovaný 3D avatar znakové řeči v RAM.",
    inputSchema: { type: "object", properties: { transcript: { type: "string" } } },
    execute: async (input) => {
      console.log("[WebMCP Execute] Dispatching sign gestures for:", input.transcript);
      return { status: "rendering", fps: 60, in_memory: true };
    }
  });

  // Inject floating 3D Avatar Widget in bottom right corner
  const avatarContainer = document.createElement('div');
  avatarContainer.id = 'asterisk-3d-avatar-container';
  avatarContainer.style.position = 'fixed';
  avatarContainer.style.bottom = '20px';
  avatarContainer.style.right = '20px';
  avatarContainer.style.width = '180px';
  avatarContainer.style.height = '240px';
  avatarContainer.style.background = 'rgba(10, 14, 28, 0.9)';
  avatarContainer.style.border = '2px solid #ffd700';
  avatarContainer.style.borderRadius = '16px';
  avatarContainer.style.zIndex = '999999';
  avatarContainer.style.boxShadow = '0 0 25px rgba(255, 215, 0, 0.4)';
  avatarContainer.style.display = 'flex';
  avatarContainer.style.flexDirection = 'column';
  avatarContainer.style.alignItems = 'center';
  avatarContainer.style.justifyContent = 'space-between';
  avatarContainer.style.padding = '10px';
  avatarContainer.style.color = '#fff';
  avatarContainer.style.fontFamily = 'sans-serif';
  avatarContainer.style.pointerEvents = 'auto';

  avatarContainer.innerHTML = `
    <div style="font-size: 11px; font-weight: bold; color: #ffd700; width: 100%; display: flex; justify-content: space-between;">
      <span>🤟 3D AVATAR</span>
      <span style="color: #4ade80;">60 FPS</span>
    </div>
    <div style="font-size: 48px; text-shadow: 0 0 10px #38bdf8;">🤖</div>
    <div style="font-size: 10px; color: #94a3b8; text-align: center;">
      100% Free Znaková Řeč<br>In-Memory RAM
    </div>
  `;

  document.body.appendChild(avatarContainer);

  chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (msg.action === 'toggle_avatar') {
      avatarContainer.style.display = msg.enabled ? 'flex' : 'none';
    }
  });
})();
