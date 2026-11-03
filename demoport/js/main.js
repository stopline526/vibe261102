(() => {
  const root = document.documentElement;

  // ===== 다크/라이트 모드 =====
  const themeToggle = document.querySelector('.theme-toggle');
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)');

  const currentTheme = () => root.dataset.theme || (prefersDark.matches ? 'dark' : 'light');

  themeToggle.addEventListener('click', () => {
    const next = currentTheme() === 'dark' ? 'light' : 'dark';
    root.dataset.theme = next;
    try { localStorage.setItem('theme', next); } catch (e) {}
  });

  // ===== 모바일 메뉴 =====
  const navToggle = document.querySelector('.nav-toggle');
  const navMenu = document.getElementById('nav-menu');

  const setMenu = (open) => {
    navMenu.classList.toggle('open', open);
    navToggle.setAttribute('aria-expanded', String(open));
    navToggle.setAttribute('aria-label', open ? '메뉴 닫기' : '메뉴 열기');
  };

  navToggle.addEventListener('click', () => setMenu(!navMenu.classList.contains('open')));
  navMenu.addEventListener('click', (e) => {
    if (e.target.closest('a')) setMenu(false);
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') setMenu(false);
  });

  // ===== 현재 섹션 메뉴 강조 =====
  const navLinks = [...navMenu.querySelectorAll('a[href^="#"]')];
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      navLinks.forEach((link) => {
        link.classList.toggle('active', link.getAttribute('href') === `#${entry.target.id}`);
      });
    });
  }, { rootMargin: '-45% 0px -50% 0px' });
  document.querySelectorAll('main section[id]').forEach((s) => observer.observe(s));

  // ===== 프로젝트 목록 =====
  const grid = document.getElementById('project-grid');

  const escapeHtml = (str = '') => str.replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[c]));

  const renderProject = (p) => {
    const thumb = p.thumbnail
      ? `<img src="${escapeHtml(p.thumbnail)}" alt="${escapeHtml(p.title)} 스크린샷" loading="lazy">`
      : `<span aria-hidden="true">${escapeHtml(p.title.charAt(0))}</span>`;
    const tags = (p.tags || []).map((t) => `<li>${escapeHtml(t)}</li>`).join('');
    const links = [
      p.github && `<a href="${escapeHtml(p.github)}" target="_blank" rel="noopener">GitHub →</a>`,
      p.demo && `<a href="${escapeHtml(p.demo)}" target="_blank" rel="noopener">Demo →</a>`
    ].filter(Boolean).join('');

    return `
      <article class="project-card">
        <div class="project-thumb">${thumb}</div>
        <div class="project-body">
          <h3>${escapeHtml(p.title)}</h3>
          <p>${escapeHtml(p.description)}</p>
          <ul class="project-tags" aria-label="사용 기술">${tags}</ul>
          <div class="project-links">${links}</div>
        </div>
      </article>`;
  };

  fetch('data/projects.json')
    .then((res) => {
      if (!res.ok) throw new Error(res.status);
      return res.json();
    })
    .then((projects) => {
      grid.innerHTML = projects.length
        ? projects.map(renderProject).join('')
        : '<p class="project-status">등록된 프로젝트가 없습니다.</p>';
    })
    .catch(() => {
      grid.innerHTML = '<p class="project-status">프로젝트를 불러오지 못했습니다. 로컬에서는 <code>python -m http.server</code>로 실행해 주세요.</p>';
    });

  // ===== 이메일 복사 =====
  const copyBtn = document.getElementById('copy-email');
  const feedback = document.getElementById('copy-feedback');

  copyBtn.addEventListener('click', async () => {
    const email = copyBtn.dataset.email;
    try {
      await navigator.clipboard.writeText(email);
      feedback.textContent = '이메일 주소를 복사했습니다.';
    } catch (e) {
      feedback.textContent = `복사에 실패했습니다: ${email}`;
    }
    setTimeout(() => { feedback.textContent = ''; }, 2500);
  });

  // ===== 연도 =====
  document.getElementById('year').textContent = new Date().getFullYear();
})();
