/**
 * DotaBlitz Frontend Application Engine
 */

class DotaBlitzApp {
  constructor() {
    this.heroes = [];
    this.currentHero = null;
    this.currentBuilds = [];
    this.activeTab = "popular";
    this.rankFilter = "all";
    this.selectedBuild = null;
    this.ws = null;
    this.gameState = null;

    this.cdnHeroBase = "https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react/heroes/";
    this.cdnItemBase = "https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react/items/";

    this.initElements();
    this.bindEvents();
  }

  initElements() {
    this.heroSearch = document.getElementById("heroSearch");
    this.heroGrid = document.getElementById("heroGrid");
    this.heroHeader = document.getElementById("heroHeader");
    this.currentHeroImg = document.getElementById("currentHeroImg");
    this.currentHeroName = document.getElementById("currentHeroName");
    this.currentHeroAttr = document.getElementById("currentHeroAttr");
    this.currentHeroType = document.getElementById("currentHeroType");
    this.currentHeroRoles = document.getElementById("currentHeroRoles");

    this.rankFilterSelect = document.getElementById("rankFilter");
    this.tabButtons = document.querySelectorAll(".tab-btn");

    this.buildWinrate = document.getElementById("buildWinrate");
    this.buildMatches = document.getElementById("buildMatches");
    this.buildSource = document.getElementById("buildSource");

    this.startingItems = document.getElementById("startingItems");
    this.earlyItems = document.getElementById("earlyItems");
    this.coreItems = document.getElementById("coreItems");
    this.lateItems = document.getElementById("lateItems");
    this.situationalItems = document.getElementById("situationalItems");

    this.skillTable = document.getElementById("skillTable");

    this.gsiIndicator = document.getElementById("gsiIndicator");
    this.gsiText = document.getElementById("gsiText");

    this.assistantGameTime = document.getElementById("assistantGameTime");
    this.assistantGold = document.getElementById("assistantGold");
    this.assistantLevel = document.getElementById("assistantLevel");
    this.assistantKDA = document.getElementById("assistantKDA");
    this.assistantNextSkill = document.getElementById("assistantNextSkill");
    this.assistantSkillSub = document.getElementById("assistantSkillSub");
    this.assistantNextItems = document.getElementById("assistantNextItems");

    this.guideModal = document.getElementById("guideModal");
    this.guideTextContent = document.getElementById("guideTextContent");
    this.exportGuideBtn = document.getElementById("exportGuideBtn");
    this.installInGameBtn = document.getElementById("installInGameBtn");
    this.closeGuideModal = document.getElementById("closeGuideModal");
    this.copyGuideBtn = document.getElementById("copyGuideBtn");
    this.downloadGuideBtn = document.getElementById("downloadGuideBtn");

    this.badAgainstRow = document.getElementById("badAgainstRow");
    this.goodAgainstRow = document.getElementById("goodAgainstRow");

    this.assistantCS = document.getElementById("assistantCS");
    this.assistantCSMin = document.getElementById("assistantCSMin");
    this.assistantCSRating = document.getElementById("assistantCSRating");

    this.timerPowerRune = document.getElementById("timerPowerRune");
    this.timerWisdomRune = document.getElementById("timerWisdomRune");
    this.timerLotus = document.getElementById("timerLotus");
    this.timerTormentor = document.getElementById("timerTormentor");
    this.timerNeutral = document.getElementById("timerNeutral");

    this.syncBtn = document.getElementById("syncBtn");
    this.openOverlayBtn = document.getElementById("openOverlayBtn");
    this.toastContainer = document.getElementById("toastContainer");
  }

  bindEvents() {
    this.heroSearch.addEventListener("input", (e) => this.filterHeroes(e.target.value));

    if (this.installInGameBtn) {
      this.installInGameBtn.addEventListener("click", () => this.handleInstallInGame());
    }

    this.tabButtons.forEach(btn => {
      btn.addEventListener("click", () => {
        this.tabButtons.forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        this.activeTab = btn.getAttribute("data-tab");
        this.renderActiveBuild();
      });
    });

    this.rankFilterSelect.addEventListener("change", (e) => {
      this.rankFilter = e.target.value;
      if (this.currentHero) {
        this.loadHeroBuilds(this.currentHero.id);
      }
    });

    this.exportGuideBtn.addEventListener("click", () => this.handleExportGuide());
    this.closeGuideModal.addEventListener("click", () => this.guideModal.classList.remove("open"));
    this.copyGuideBtn.addEventListener("click", () => this.copyGuideToClipboard());
    this.downloadGuideBtn.addEventListener("click", () => this.downloadGuideFile());

    this.syncBtn.addEventListener("click", () => this.triggerDataSync());
    this.openOverlayBtn.addEventListener("click", () => {
      window.open("/overlay.html", "DotaBlitzOverlay", "width=380,height=520,toolbar=no,menubar=no");
    });
  }

  async init() {
    await this.loadHeroes();
    this.connectWebSocket();
    this.checkSyncStatus();

    // Select default hero (e.g. Pudge or first)
    if (this.heroes.length > 0) {
      const pudge = this.heroes.find(h => h.name === "pudge") || this.heroes[0];
      this.selectHero(pudge);
    }
  }

  async loadHeroes() {
    try {
      const res = await fetch("/api/heroes");
      if (res.ok) {
        this.heroes = await res.json();
        this.renderHeroGrid(this.heroes);
      } else {
        this.showToast("Failed to fetch heroes from local backend", "error");
      }
    } catch (err) {
      console.error("Error loading heroes:", err);
      this.showToast("Backend connection error", "error");
    }
  }

  renderHeroGrid(heroesList) {
    this.heroGrid.innerHTML = "";
    heroesList.forEach(hero => {
      const item = document.createElement("div");
      item.className = "hero-item";
      if (this.currentHero && this.currentHero.id === hero.id) {
        item.classList.add("active");
      }

      const img = document.createElement("img");
      img.src = `${this.cdnHeroBase}${hero.name}.png`;
      img.alt = hero.localized_name;
      img.loading = "lazy";
      img.onerror = () => { img.src = "https://via.placeholder.com/80x45/182030/ffffff?text=" + hero.localized_name.charAt(0); };

      const label = document.createElement("div");
      label.className = "hero-label";
      label.textContent = hero.localized_name;

      item.appendChild(img);
      item.appendChild(label);
      item.addEventListener("click", () => this.selectHero(hero));

      this.heroGrid.appendChild(item);
    });
  }

  filterHeroes(query) {
    const q = query.toLowerCase().trim();
    const filtered = this.heroes.filter(h =>
      h.localized_name.toLowerCase().includes(q) || h.name.toLowerCase().includes(q)
    );
    this.renderHeroGrid(filtered);
  }

  async selectHero(hero) {
    this.currentHero = hero;

    // Highlight in grid
    document.querySelectorAll(".hero-item").forEach(el => el.classList.remove("active"));

    // Update Header
    this.currentHeroImg.src = `${this.cdnHeroBase}${hero.name}.png`;
    this.currentHeroName.textContent = hero.localized_name;
    this.currentHeroAttr.textContent = hero.primary_attr.toUpperCase();
    this.currentHeroAttr.className = `badge badge-${hero.primary_attr}`;
    this.currentHeroType.textContent = hero.attack_type;
    this.currentHeroRoles.textContent = hero.roles.length ? `• ${hero.roles.slice(0, 3).join(", ")}` : "";

    await Promise.all([
      this.loadHeroBuilds(hero.id),
      this.loadHeroMatchups(hero.id)
    ]);
  }

  async loadHeroMatchups(heroId) {
    if (!this.badAgainstRow || !this.goodAgainstRow) return;
    this.badAgainstRow.innerHTML = '<span style="font-size:11px;color:var(--text-muted);">Carregando matchups...</span>';
    this.goodAgainstRow.innerHTML = '<span style="font-size:11px;color:var(--text-muted);">Carregando matchups...</span>';

    try {
      const res = await fetch(`/api/heroes/${heroId}/matchups`);
      if (res.ok) {
        const data = await res.json();
        this.renderMatchupList(this.badAgainstRow, data.bad_against || [], false);
        this.renderMatchupList(this.goodAgainstRow, data.good_against || [], true);
      }
    } catch (e) {
      console.warn("Could not load matchups:", e);
    }
  }

  renderMatchupList(container, matchups, isPositive) {
    container.innerHTML = "";
    if (matchups.length === 0) {
      container.innerHTML = '<span style="font-size:11px;color:var(--text-muted);">Sem dados suficientes</span>';
      return;
    }

    matchups.forEach(m => {
      const wrapper = document.createElement("div");
      wrapper.className = "hero-item";
      wrapper.style.width = "48px";
      wrapper.style.height = "32px";
      wrapper.title = `${m.localized_name}: ${m.winrate_vs}% winrate (${m.games} partidas)`;

      const img = document.createElement("img");
      img.src = m.img;
      img.alt = m.localized_name;
      img.onerror = () => { img.src = "https://via.placeholder.com/48x32/121824/ffffff?text=" + m.localized_name.charAt(0); };

      const badge = document.createElement("div");
      badge.style.position = "absolute";
      badge.style.bottom = "0";
      badge.style.right = "0";
      badge.style.fontSize = "8px";
      badge.style.fontWeight = "800";
      badge.style.padding = "1px 2px";
      badge.style.borderRadius = "2px";
      badge.style.background = isPositive ? "rgba(0, 212, 170, 0.9)" : "rgba(214, 48, 49, 0.9)";
      badge.style.color = "#000";
      badge.textContent = `${m.winrate_vs}%`;

      wrapper.appendChild(img);
      wrapper.appendChild(badge);
      container.appendChild(wrapper);
    });
  }

  async handleInstallInGame() {
    if (!this.selectedBuild) {
      this.showToast("Selecione uma build primeiro!", "error");
      return;
    }

    try {
      this.installInGameBtn.disabled = true;
      this.installInGameBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Instalando...';

      const res = await fetch(`/api/guides/install-in-game/${this.selectedBuild.id}`, { method: "POST" });
      if (res.ok) {
        const data = await res.json();
        this.showToast(`⚡ Guia de ${this.currentHero.localized_name} aplicado diretamente no Dota 2!`, "success");
      } else {
        const err = await res.json();
        this.showToast(err.detail || "Erro ao instalar guia no Dota 2", "error");
      }
    } catch (e) {
      this.showToast("Falha na comunicação com o Dota 2", "error");
    } finally {
      this.installInGameBtn.disabled = false;
      this.installInGameBtn.innerHTML = '<i class="fa-solid fa-bolt"></i> Aplicar no Dota 2';
    }
  }

  async loadHeroBuilds(heroId) {
    try {
      const res = await fetch(`/api/builds/${heroId}?rank_filter=${this.rankFilter}`);
      if (res.ok) {
        const data = await res.json();
        this.currentBuilds = data.builds || [];
        this.renderActiveBuild();
      } else {
        // Fallback default builds structure if DB has no cache yet
        this.currentBuilds = this.generateFallbackBuilds(heroId);
        this.renderActiveBuild();
      }
    } catch (err) {
      console.warn("Could not load builds, using cached structure:", err);
      this.currentBuilds = this.generateFallbackBuilds(heroId);
      this.renderActiveBuild();
    }
  }

  generateFallbackBuilds(heroId) {
    return [
      {
        id: 1,
        hero_id: heroId,
        build_type: "popular",
        source: "opendota",
        winrate: 52.4,
        sample_size: 14250,
        items_starting: ["tango", "flask", "branches", "branches", "quelling_blade", "circlet"],
        items_early: ["magic_wand", "boots", "bracer", "bracer"],
        items_core: ["power_treads", "blink", "black_king_bar"],
        items_late: ["heart", "assault", "shivas_guard", "overwhelming_blink"],
        items_situational: ["blade_mail", "lotus_orb", "aeon_disk", "pipe"],
        skill_order: [0, 1, 0, 2, 0, 3, 0, 1, 1, 4, 1, 3, 2, 2, 5, 2, 3, 6, 7]
      },
      {
        id: 2,
        hero_id: heroId,
        build_type: "winrate",
        source: "dotabuff",
        winrate: 55.8,
        sample_size: 3410,
        items_starting: ["tango", "clarity", "branches", "quelling_blade", "gauntlets"],
        items_early: ["phase_boots", "urn_of_shadows", "soul_ring"],
        items_core: ["spirit_vessel", "blink", "aghanims_scepter"],
        items_late: ["octarine_core", "shivas_guard", "refresher"],
        items_situational: ["glimmer_cape", "force_staff", "heavens_halberd"],
        skill_order: [1, 0, 1, 2, 1, 3, 1, 0, 0, 4, 0, 3, 2, 2, 5, 2, 3, 6, 7]
      },
      {
        id: 3,
        hero_id: heroId,
        build_type: "meta",
        source: "opendota",
        winrate: 54.1,
        sample_size: 580,
        items_starting: ["tango", "flask", "branches", "magic_stick"],
        items_early: ["tranquil_boots", "magic_wand", "wind_lace"],
        items_core: ["blink", "aghanims_shard", "black_king_bar"],
        items_late: ["octarine_core", "wind_waker", "scythe_of_vyse"],
        items_situational: ["lotus_orb", "pipe", "crimson_guard"],
        skill_order: [0, 1, 0, 1, 0, 3, 0, 1, 1, 4, 2, 3, 2, 2, 5, 2, 3, 6, 7]
      },
      {
        id: 4,
        hero_id: heroId,
        build_type: "situational",
        source: "aggregated",
        winrate: 51.5,
        sample_size: 890,
        items_starting: ["tango", "branches", "ring_of_protection"],
        items_early: ["arcane_boots", "magic_wand"],
        items_core: ["blade_mail", "heart", "aghanims_scepter"],
        items_late: ["bloodstone", "assault", "abyssal_blade"],
        items_situational: ["nullifier", "silver_edge"],
        skill_order: [0, 2, 0, 2, 0, 3, 0, 2, 2, 4, 1, 3, 1, 1, 5, 1, 3, 6, 7]
      }
    ];
  }

  renderActiveBuild() {
    let build = this.currentBuilds.find(b => b.build_type === this.activeTab);
    if (!build && this.currentBuilds.length > 0) {
      build = this.currentBuilds[0];
    }
    this.selectedBuild = build;

    if (!build) return;

    // Stats
    this.buildWinrate.textContent = `${build.winrate ? build.winrate.toFixed(1) : "50.0"}%`;
    this.buildMatches.textContent = `${(build.sample_size || 0).toLocaleString()} matches`;
    this.buildSource.textContent = build.source || "aggregated";

    // Items
    this.renderItemRow(this.startingItems, build.items_starting || []);
    this.renderItemRow(this.earlyItems, build.items_early || []);
    this.renderItemRow(this.coreItems, build.items_core || []);
    this.renderItemRow(this.lateItems, build.items_late || []);
    this.renderItemRow(this.situationalItems, build.items_situational || []);

    // Skills
    this.renderSkillTable(build.skill_order || []);

    // Update Assistant Recommendations
    this.updateAssistantFromBuild(build);
  }

  renderItemRow(container, items) {
    container.innerHTML = "";
    if (!items || items.length === 0) {
      container.innerHTML = '<span style="font-size:12px;color:var(--text-muted);">None listed</span>';
      return;
    }

    items.forEach(item => {
      const cleanName = String(item).replace(/^item_/, "").trim().toLowerCase();
      const prettyName = cleanName.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase());

      const wrapper = document.createElement("div");
      wrapper.className = "item-icon-wrapper";
      wrapper.title = prettyName;

      const img = document.createElement("img");
      img.src = `${this.cdnItemBase}${cleanName}.png`;
      img.alt = prettyName;

      // Smart fallback: try legacy Steam CDN format, then placeholder
      img.onerror = () => {
        if (!img.dataset.triedLegacy) {
          img.dataset.triedLegacy = "true";
          img.src = `https://cdn.cloudflare.steamstatic.com/apps/dota2/images/items/${cleanName}_lg.png`;
        } else {
          img.src = "https://via.placeholder.com/52x38/182030/ffffff?text=" + encodeURIComponent(prettyName.slice(0, 5));
        }
      };

      wrapper.appendChild(img);
      container.appendChild(wrapper);
    });
  }

  renderSkillTable(order) {
    if (!order || order.length === 0) {
      this.skillTable.innerHTML = "<tr><td>No skill order data available</td></tr>";
      return;
    }

    const maxLvl = Math.min(order.length, 25);
    let html = "<thead><tr><th>Skill</th>";
    for (let i = 1; i <= maxLvl; i++) {
      html += `<th>${i}</th>`;
    }
    html += "</tr></thead><tbody>";

    const skills = [
      { key: 0, label: "Q", class: "skill-q" },
      { key: 1, label: "W", class: "skill-w" },
      { key: 2, label: "E", class: "skill-e" },
      { key: 3, label: "R", class: "skill-r" }
    ];

    skills.forEach(s => {
      html += `<tr><td class="skill-label-cell ${s.class}">${s.label}</td>`;
      for (let lvl = 0; lvl < maxLvl; lvl++) {
        if (order[lvl] === s.key) {
          html += `<td style="background: rgba(255,255,255,0.06);"><span class="skill-point ${s.class}"></span></td>`;
        } else {
          html += `<td style="color: var(--text-muted);">-</td>`;
        }
      }
      html += "</tr>";
    });

    html += "</tbody>";
    this.skillTable.innerHTML = html;
  }

  updateAssistantFromBuild(build) {
    if (!build) return;
    const currentLevel = this.gameState ? this.gameState.hero_level : 1;
    const skillOrder = build.skill_order || [];

    const skillLabels = ["Q", "W", "E", "R", "Talent (L10)", "Talent (L15)", "Talent (L20)", "Talent (L25)"];
    const nextSkillIdx = skillOrder[currentLevel - 1];

    if (nextSkillIdx !== undefined) {
      const label = skillLabels[nextSkillIdx] || `Skill ${nextSkillIdx}`;
      this.assistantNextSkill.textContent = label;
      this.assistantSkillSub.textContent = `For Hero Level ${currentLevel}`;
    }

    // Render next items from core
    const nextItems = (build.items_core || []).slice(0, 3);
    this.renderItemRow(this.assistantNextItems, nextItems);
  }

  connectWebSocket() {
    const wsUrl = `ws://${window.location.host}/ws`;
    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        this.updateGSIStatus(false, "Waiting for match data");
      };

      this.ws.onmessage = (event) => {
        try {
          const state = JSON.parse(event.data);
          this.handleGSIUpdate(state);
        } catch (e) {
          console.error("WS Parse error:", e);
        }
      };

      this.ws.onclose = () => {
        this.updateGSIStatus(false, "Disconnected (reconnecting...)");
        setTimeout(() => this.connectWebSocket(), 3000);
      };

      this.ws.onerror = () => {
        this.updateGSIStatus(false, "Not connected");
      };
    } catch (e) {
      console.warn("WebSocket not supported or failed:", e);
    }
  }

  updateGSIStatus(connected, text) {
    if (connected) {
      this.gsiIndicator.className = "status-indicator connected";
      this.gsiText.textContent = `Dota 2: In-Game`;
    } else {
      this.gsiIndicator.className = "status-indicator disconnected";
      this.gsiText.textContent = `Dota 2: ${text}`;
    }
  }

  handleGSIUpdate(state) {
    this.gameState = state;
    this.updateGSIStatus(true, "In-Game");

    // Game stats
    const minutes = Math.floor(state.game_time / 60);
    const seconds = state.game_time % 60;
    this.assistantGameTime.textContent = `${minutes}:${seconds < 10 ? '0' : ''}${seconds}`;
    this.assistantGold.textContent = (state.gold || 0).toLocaleString();
    this.assistantLevel.textContent = state.hero_level || 1;
    this.assistantKDA.textContent = `${state.kills || 0}/${state.deaths || 0}/${state.assists || 0}`;

    // CS & Efficiency
    if (this.assistantCS) {
      this.assistantCS.textContent = `${state.last_hits || 0}/${state.denies || 0}`;
    }
    if (this.assistantCSMin) {
      this.assistantCSMin.textContent = `${(state.cs_per_min || 0).toFixed(1)} CS/min`;
    }
    if (this.assistantCSRating) {
      this.assistantCSRating.textContent = `Rating ${state.cs_rating || 'A'}`;
      this.assistantCSRating.style.color = (state.cs_rating === 'S+' || state.cs_rating === 'S') ? 'var(--accent-primary)' : 'var(--text-main)';
    }

    // Tactical Timers
    if (this.timerPowerRune && state.next_power_rune_sec !== undefined) {
      this.timerPowerRune.textContent = this.formatTimer(state.next_power_rune_sec);
    }
    if (this.timerWisdomRune && state.next_wisdom_rune_sec !== undefined) {
      this.timerWisdomRune.textContent = this.formatTimer(state.next_wisdom_rune_sec);
    }
    if (this.timerLotus && state.next_lotus_sec !== undefined) {
      this.timerLotus.textContent = this.formatTimer(state.next_lotus_sec);
    }
    if (this.timerTormentor && state.next_tormentor_sec !== undefined) {
      this.timerTormentor.textContent = (state.clock_time >= 1200) ? "Disponível no Mapa" : this.formatTimer(state.next_tormentor_sec);
    }
    if (this.timerNeutral && state.next_neutral_tier !== undefined) {
      this.timerNeutral.textContent = `Tier ${state.next_neutral_tier} em ${this.formatTimer(state.next_neutral_tier_sec || 0)}`;
    }

    // Auto-detect hero pick
    if (state.hero_name && (!this.currentHero || this.currentHero.name !== state.hero_name)) {
      const matched = this.heroes.find(h => h.name === state.hero_name);
      if (matched) {
        this.selectHero(matched);
        this.showToast(`Hero detected: ${matched.localized_name}!`, "success");
      }
    }

    if (this.selectedBuild) {
      this.updateAssistantFromBuild(this.selectedBuild);
    }
  }

  formatTimer(totalSeconds) {
    if (totalSeconds <= 0) return "00:00";
    const m = Math.floor(totalSeconds / 60);
    const s = totalSeconds % 60;
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  }

  async handleExportGuide() {
    if (!this.selectedBuild) return;
    try {
      const res = await fetch(`/api/guides/generate/${this.selectedBuild.id}`, { method: "POST" });
      if (res.ok) {
        const data = await res.json();
        this.guideTextContent.value = data.content;
        this.guideModal.classList.add("open");
      } else {
        // Fallback: generate client side text
        this.guideTextContent.value = this.generateClientGuideText();
        this.guideModal.classList.add("open");
      }
    } catch (e) {
      this.guideTextContent.value = this.generateClientGuideText();
      this.guideModal.classList.add("open");
    }
  }

  generateClientGuideText() {
    const heroName = this.currentHero ? this.currentHero.localized_name : "Hero";
    const b = this.selectedBuild;
    return `[h1]${heroName} – DotaBlitz ${b.build_type.toUpperCase()} Build[/h1]
[b]Winrate:[/b] ${b.winrate}% (${b.sample_size} matches)
[b]Source:[/b] ${b.source}

[h2]Starting Items[/h2]
${(b.items_starting || []).map(i => `• ${i}`).join("\n")}

[h2]Early Game[/h2]
${(b.items_early || []).map(i => `• ${i}`).join("\n")}

[h2]Core Items[/h2]
${(b.items_core || []).map(i => `• ${i}`).join("\n")}

[h2]Late Game[/h2]
${(b.items_late || []).map(i => `• ${i}`).join("\n")}

[h2]Situational[/h2]
${(b.items_situational || []).map(i => `• ${i}`).join("\n")}

Generated automatically by DotaBlitz Companion.`;
  }

  copyGuideToClipboard() {
    this.guideTextContent.select();
    navigator.clipboard.writeText(this.guideTextContent.value);
    this.showToast("Guide copied to clipboard!", "success");
  }

  downloadGuideFile() {
    const text = this.guideTextContent.value;
    const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${this.currentHero ? this.currentHero.name : 'dota2'}_dotablitz_guide.txt`;
    a.click();
    URL.revokeObjectURL(url);
    this.showToast("Guide file downloaded!", "success");
  }

  async triggerDataSync() {
    this.syncBtn.classList.add("fa-spin");
    this.showToast("Synchronizing builds with OpenDota & Dotabuff...", "info");
    try {
      const res = await fetch(`/api/sync/trigger?rank_filter=${this.rankFilter}`, { method: "POST" });
      if (res.ok) {
        this.showToast("Sync job dispatched!", "success");
      }
    } catch (e) {
      this.showToast("Sync trigger failed", "error");
    } finally {
      setTimeout(() => this.syncBtn.classList.remove("fa-spin"), 1500);
    }
  }

  async checkSyncStatus() {
    try {
      const res = await fetch("/api/sync/status");
      if (res.ok) {
        const data = await res.json();
        const patchElem = document.getElementById("statusPatch");
        const syncElem = document.getElementById("statusSync");
        if (data.current_patch) patchElem.textContent = `Dota 2 Patch: ${data.current_patch}`;
        syncElem.textContent = `Cache: ${data.heroes_count} heroes, ${data.builds_count} builds`;
      }
    } catch (e) {}
  }

  showToast(message, type = "info") {
    const toast = document.createElement("div");
    toast.className = "toast";
    const icon = type === "success" ? "fa-circle-check" : type === "error" ? "fa-circle-xmark" : "fa-circle-info";
    const color = type === "success" ? "var(--accent-primary)" : type === "error" ? "var(--accent-danger)" : "var(--accent-secondary)";

    toast.innerHTML = `<i class="fa-solid ${icon}" style="color:${color}"></i><span>${message}</span>`;
    this.toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transition = "opacity 0.4s ease";
      setTimeout(() => toast.remove(), 400);
    }, 3500);
  }
}

// Instantiate on DOM load
window.addEventListener("DOMContentLoaded", () => {
  window.dotablitz = new DotaBlitzApp();
  window.dotablitz.init();
});
