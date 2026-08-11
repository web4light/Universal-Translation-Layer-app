// ============================================================================
// Bifrost Gate — Universal Translation Layer
// Latin splash → language pick → Bifrost tunnel → morphed text → Midgard
// ============================================================================

// === ALL LANGUAGES (full world coverage) ===
const LANGUAGES = {
    // Slavic
    cs: { flag: '🇨🇿' },
    sk: { flag: '🇸🇰' },
    pl: { flag: '🇵🇱' },
    uk: { flag: '🇺🇦' },
    ru: { flag: '🇷🇺' },
    sr: { flag: '🇷🇸' },
    hr: { flag: '🇭🇷' },
    bg: { flag: '🇧🇬' },
    sl: { flag: '🇸🇮' },
    // Germanic
    en: { flag: '🇬🇧' },
    de: { flag: '🇩🇪' },
    nl: { flag: '🇳🇱' },
    sv: { flag: '🇸🇪' },
    da: { flag: '🇩🇰' },
    no: { flag: '🇳🇴' },
    is: { flag: '🇮🇸' },
    // Romance
    fr: { flag: '🇫🇷' },
    es: { flag: '🇪🇸' },
    it: { flag: '🇮🇹' },
    pt: { flag: '🇵🇹' },
    ro: { flag: '🇷🇴' },
    ca: { flag: '🏴' },
    // Asian
    ja: { flag: '🇯🇵' },
    zh: { flag: '🇨🇳' },
    ko: { flag: '🇰🇷' },
    vi: { flag: '🇻🇳' },
    th: { flag: '🇹🇭' },
    hi: { flag: '🇮🇳' },
    bn: { flag: '🇧🇩' },
    id: { flag: '🇮🇩' },
    ms: { flag: '🇲🇾' },
    tl: { flag: '🇵🇭' },
    // Semitic & Afro-Asiatic
    ar: { flag: '🇸🇦' },
    he: { flag: '🇮🇱' },
    fa: { flag: '🇮🇷' },
    tr: { flag: '🇹🇷' },
    // Finno-Ugric & Baltic
    fi: { flag: '🇫🇮' },
    hu: { flag: '🇭🇺' },
    et: { flag: '🇪🇪' },
    lv: { flag: '🇱🇻' },
    lt: { flag: '🇱🇹' },
    // Celtic & Other
    ga: { flag: '🇮🇪' },
    el: { flag: '🇬🇷' },
    ka: { flag: '🇬🇪' },
    sw: { flag: '🇰🇪' },
    am: { flag: '🇪🇹' },
};

// === TRANSLATIONS for each language ===
const TRANSLATIONS = {
    motto1: {
        la: 'Loquere lingua tua.',
        cs: 'Mluv svým jazykem.',
        sk: 'Hovor svojím jazykom.',
        pl: 'Mów swoim językiem.',
        uk: 'Говори своєю мовою.',
        ru: 'Говори на своём языке.',
        sr: 'Говори својим језиком.',
        hr: 'Govori svojim jezikom.',
        bg: 'Говори на своя език.',
        sl: 'Govori v svojem jeziku.',
        en: 'Speak your language.',
        de: 'Sprich deine Sprache.',
        nl: 'Spreek je eigen taal.',
        sv: 'Tala ditt språk.',
        da: 'Tal dit sprog.',
        no: 'Snakk ditt språk.',
        is: 'Talaðu þitt tungumál.',
        fr: 'Parle ta langue.',
        es: 'Habla tu idioma.',
        it: 'Parla la tua lingua.',
        pt: 'Fala a tua língua.',
        ro: 'Vorbește limba ta.',
        ca: 'Parla la teva llengua.',
        ja: 'あなたの言葉で話そう。',
        zh: '说你自己的语言。',
        ko: '당신의 언어로 말하세요.',
        vi: 'Hãy nói ngôn ngữ của bạn.',
        th: 'พูดภาษาของคุณ',
        hi: 'अपनी भाषा बोलो।',
        bn: 'তোমার ভাষায় কথা বলো।',
        id: 'Bicaralah dalam bahasamu.',
        ms: 'Bertutur dalam bahasa anda.',
        tl: 'Magsalita sa iyong wika.',
        ar: 'تكلّم بلغتك.',
        he: 'דבר בשפה שלך.',
        fa: 'به زبان خودت صحبت کن.',
        tr: 'Kendi dilinde konuş.',
        fi: 'Puhu omaa kieltäsi.',
        hu: 'Beszélj a saját nyelveden.',
        et: 'Räägi oma keeles.',
        lv: 'Runā savā valodā.',
        lt: 'Kalbėk savo kalba.',
        ga: 'Labhair do theanga féin.',
        el: 'Μίλα τη γλώσσα σου.',
        ka: 'ილაპარაკე შენს ენაზე.',
        sw: 'Ongea lugha yako.',
        am: 'በቋንቋህ ተናገር።',
    },
    motto2: {
        la: 'Omnes te audient sua lingua.',
        cs: 'Všichni tě uslyší ve svém jazyce.',
        sk: 'Všetci ťa počujú vo svojom jazyku.',
        pl: 'Wszyscy usłyszą cię w swoim języku.',
        uk: 'Усі почують тебе своєю мовою.',
        ru: 'Все услышат тебя на своём языке.',
        sr: 'Сви ће те чути на свом језику.',
        hr: 'Svi će te čuti na svom jeziku.',
        bg: 'Всички ще те чуят на своя език.',
        sl: 'Vsi te bodo slišali v svojem jeziku.',
        en: 'Everyone hears you in theirs.',
        de: 'Jeder hört dich in seiner Sprache.',
        nl: 'Iedereen hoort je in hun eigen taal.',
        sv: 'Alla hör dig på sitt språk.',
        da: 'Alle hører dig på deres sprog.',
        no: 'Alle hører deg på sitt språk.',
        is: 'Allir heyra þig á sínu tungumáli.',
        fr: 'Tous t\'entendent dans leur langue.',
        es: 'Todos te escuchan en su idioma.',
        it: 'Tutti ti ascoltano nella loro lingua.',
        pt: 'Todos te ouvem na sua língua.',
        ro: 'Toți te aud în limba lor.',
        ca: 'Tothom t\'escolta en la seva llengua.',
        ja: '誰もが自分の言語であなたを聞く。',
        zh: '每个人都用自己的语言听到你。',
        ko: '모두가 자신의 언어로 당신을 듣습니다.',
        vi: 'Mọi người nghe bạn bằng ngôn ngữ của họ.',
        th: 'ทุกคนได้ยินคุณในภาษาของพวกเขา',
        hi: 'सब अपनी भाषा में तुम्हें सुनेंगे।',
        bn: 'সবাই তোমাকে নিজের ভাষায় শুনবে।',
        id: 'Semua mendengarmu dalam bahasa mereka.',
        ms: 'Semua orang mendengar anda dalam bahasa mereka.',
        tl: 'Maririnig ka ng lahat sa kanilang wika.',
        ar: 'الجميع يسمعك بلغتهم.',
        he: 'כולם שומעים אותך בשפה שלהם.',
        fa: 'همه تو را به زبان خودشان می‌شنوند.',
        tr: 'Herkes seni kendi dilinde duyar.',
        fi: 'Kaikki kuulevat sinut omalla kielellään.',
        hu: 'Mindenki a saját nyelvén hall téged.',
        et: 'Kõik kuulevad sind oma keeles.',
        lv: 'Visi tevi dzird savā valodā.',
        lt: 'Visi girdi tave savo kalba.',
        ga: 'Cloiseann gach duine thú ina dteanga féin.',
        el: 'Όλοι σε ακούν στη γλώσσα τους.',
        ka: 'ყველა გისმენს თავის ენაზე.',
        sw: 'Kila mtu anakusikia kwa lugha yake.',
        am: 'ሁሉም በቋንቋቸው ይሰሙሃል።',
    },
    motto3: {
        la: 'Tua voce.',
        cs: 'Tvým hlasem.',
        sk: 'Tvojím hlasom.',
        pl: 'Twoim głosem.',
        uk: 'Твоїм голосом.',
        ru: 'Твоим голосом.',
        sr: 'Твојим гласом.',
        hr: 'Tvojim glasom.',
        bg: 'С твоя глас.',
        sl: 'S tvojim glasom.',
        en: 'In your voice.',
        de: 'Mit deiner Stimme.',
        nl: 'Met jouw stem.',
        sv: 'Med din röst.',
        da: 'Med din stemme.',
        no: 'Med din stemme.',
        is: 'Með þinni röddu.',
        fr: 'Avec ta voix.',
        es: 'Con tu voz.',
        it: 'Con la tua voce.',
        pt: 'Com a tua voz.',
        ro: 'Cu vocea ta.',
        ca: 'Amb la teva veu.',
        ja: 'あなたの声で。',
        zh: '用你的声音。',
        ko: '당신의 목소리로.',
        vi: 'Bằng giọng của bạn.',
        th: 'ด้วยเสียงของคุณ',
        hi: 'तुम्हारी आवाज़ में।',
        bn: 'তোমার কণ্ঠে।',
        id: 'Dengan suaramu.',
        ms: 'Dengan suara anda.',
        tl: 'Sa iyong boses.',
        ar: 'بصوتك.',
        he: 'בקול שלך.',
        fa: 'با صدای خودت.',
        tr: 'Senin sesinle.',
        fi: 'Sinun äänelläsi.',
        hu: 'A te hangoddal.',
        et: 'Sinu häälega.',
        lv: 'Ar tavu balsi.',
        lt: 'Tavo balsu.',
        ga: 'Le do ghuth féin.',
        el: 'Με τη φωνή σου.',
        ka: 'შენი ხმით.',
        sw: 'Kwa sauti yako.',
        am: 'በድምፅህ።',
    },
    welcome: {
        la: 'Salvete in Midgard',
        cs: 'Vítejte na Midgardu',
        sk: 'Vitajte na Midgarde',
        pl: 'Witajcie na Midgardzie',
        uk: 'Ласкаво просимо до Мідгарда',
        ru: 'Добро пожаловать в Мидгард',
        sr: 'Добродошли у Мидгард',
        hr: 'Dobrodošli u Midgard',
        bg: 'Добре дошли в Мидгард',
        sl: 'Dobrodošli v Midgard',
        en: 'Welcome to Midgard',
        de: 'Willkommen in Midgard',
        nl: 'Welkom in Midgard',
        sv: 'Välkommen till Midgard',
        da: 'Velkommen til Midgard',
        no: 'Velkommen til Midgard',
        is: 'Velkomin til Miðgarðs',
        fr: 'Bienvenue à Midgard',
        es: 'Bienvenido a Midgard',
        it: 'Benvenuto a Midgard',
        pt: 'Bem-vindo a Midgard',
        ro: 'Bine ați venit în Midgard',
        ca: 'Benvingut a Midgard',
        ja: 'ミッドガルドへようこそ',
        zh: '欢迎来到米德加尔德',
        ko: '미드가르드에 오신 것을 환영합니다',
        vi: 'Chào mừng đến Midgard',
        th: 'ยินดีต้อนรับสู่มิดการ์ด',
        hi: 'मिडगार्ड में आपका स्वागत है',
        bn: 'মিডগার্ডে স্বাগতম',
        id: 'Selamat datang di Midgard',
        ms: 'Selamat datang ke Midgard',
        tl: 'Maligayang pagdating sa Midgard',
        ar: 'مرحباً بكم في ميدغارد',
        he: 'ברוכים הבאים למידגארד',
        fa: 'به میدگارد خوش آمدید',
        tr: 'Midgard\'a hoş geldiniz',
        fi: 'Tervetuloa Midgardiin',
        hu: 'Üdvözöljük Midgardban',
        et: 'Tere tulemast Midgardi',
        lv: 'Laipni lūdzam Midgardā',
        lt: 'Sveiki atvykę į Midgardą',
        ga: 'Fáilte go Midgard',
        el: 'Καλώς ήρθατε στο Μίντγκαρντ',
        ka: 'კეთილი იყოს თქვენი მობრძანება მიდგარდში',
        sw: 'Karibu Midgard',
        am: 'ወደ ሚድጋርድ እንኳን ደህና መጡ',
    },
    subtitle: {
        la: 'Translatio universalis parata est.',
        cs: 'Univerzální překlad je připraven.',
        sk: 'Univerzálny preklad je pripravený.',
        pl: 'Uniwersalne tłumaczenie jest gotowe.',
        uk: 'Універсальний переклад готовий.',
        ru: 'Универсальный перевод готов.',
        sr: 'Универзални превод је спреман.',
        hr: 'Univerzalni prijevod je spreman.',
        bg: 'Универсалният превод е готов.',
        sl: 'Univerzalni prevod je pripravljen.',
        en: 'Universal translation is ready.',
        de: 'Universelle Übersetzung ist bereit.',
        nl: 'Universele vertaling is gereed.',
        sv: 'Universell översättning är redo.',
        da: 'Universel oversættelse er klar.',
        no: 'Universell oversettelse er klar.',
        is: 'Alhliða þýðing er tilbúin.',
        fr: 'La traduction universelle est prête.',
        es: 'La traducción universal está lista.',
        it: 'La traduzione universale è pronta.',
        pt: 'A tradução universal está pronta.',
        ro: 'Traducerea universală este pregătită.',
        ca: 'La traducció universal està preparada.',
        ja: 'ユニバーサル翻訳の準備ができました。',
        zh: '通用翻译已就绪。',
        ko: '범용 번역이 준비되었습니다.',
        vi: 'Dịch thuật phổ quát đã sẵn sàng.',
        th: 'การแปลสากลพร้อมแล้ว',
        hi: 'सार्वभौमिक अनुवाद तैयार है।',
        bn: 'সার্বজনীন অনুবাদ প্রস্তুত।',
        id: 'Terjemahan universal siap.',
        ms: 'Terjemahan universal sedia.',
        tl: 'Ang unibersal na pagsasalin ay handa na.',
        ar: 'الترجمة الشاملة جاهزة.',
        he: 'התרגום האוניברסלי מוכן.',
        fa: 'ترجمه جهانی آماده است.',
        tr: 'Evrensel çeviri hazır.',
        fi: 'Universaali käännös on valmis.',
        hu: 'Az univerzális fordítás kész.',
        et: 'Universaalne tõlge on valmis.',
        lv: 'Universālais tulkojums ir gatavs.',
        lt: 'Universalus vertimas paruoštas.',
        ga: 'Tá an t-aistriúchán uilíoch réidh.',
        el: 'Η καθολική μετάφραση είναι έτοιμη.',
        ka: 'უნივერსალური თარგმანი მზადაა.',
        sw: 'Tafsiri ya ulimwengu iko tayari.',
        am: 'ዓለም አቀፍ ትርጉም ዝግጁ ነው።',
    },
};

// Midgard dashboard links (translated would be overkill, keep universal)
const MIDGARD_LINKS = [
    { icon: '🗣️', name: 'Karel IV.', href: 'karel.html' },
    { icon: '🌐', name: 'Mesh', href: 'mesh.html' },
    { icon: '🤖', name: 'Agents', href: 'agents.html' },
    { icon: '🏛️', name: 'Mincovna', href: 'mint.html' },
    { icon: '🛡️', name: 'Geall', href: 'geall.html' },
];

// ============================================================================
// INITIALIZATION
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    buildLanguageGrid();
});

function buildLanguageGrid() {
    const grid = document.getElementById('lang-grid');
    for (const [code, lang] of Object.entries(LANGUAGES)) {
        const btn = document.createElement('button');
        btn.className = 'lang-btn';
        btn.textContent = lang.flag;
        btn.onclick = () => activateBifrost(code);
        grid.appendChild(btn);
    }
}

// ============================================================================
// BIFROST TUNNEL ACTIVATION
// ============================================================================

function activateBifrost(langCode) {
    const splash = document.getElementById('splash');
    const bifrost = document.getElementById('bifrost');

    // Hide splash
    splash.classList.add('hidden');

    // Show Bifrost
    setTimeout(() => {
        bifrost.classList.add('active');
        createRings();
        startTextMorph(langCode);
    }, 400);
}

function createRings() {
    const container = document.getElementById('rings-container');
    container.innerHTML = '';

    const colors = [
        'rgba(255, 0, 80, 0.6)',
        'rgba(255, 127, 0, 0.6)',
        'rgba(255, 255, 0, 0.5)',
        'rgba(0, 255, 100, 0.5)',
        'rgba(0, 180, 255, 0.6)',
        'rgba(110, 68, 255, 0.6)',
        'rgba(200, 50, 255, 0.5)',
    ];

    // Create 20 rings with staggered animations
    for (let i = 0; i < 20; i++) {
        const ring = document.createElement('div');
        ring.className = 'ring';
        const size = 50 + Math.random() * 100;
        const color = colors[i % colors.length];
        ring.style.width = size + 'px';
        ring.style.height = size + 'px';
        ring.style.borderColor = color;
        ring.style.boxShadow = `0 0 10px ${color}, inset 0 0 10px ${color}`;
        ring.style.animationDelay = (i * 0.15) + 's';
        ring.style.animationDuration = (1.5 + Math.random()) + 's';
        container.appendChild(ring);
    }
}

// ============================================================================
// TEXT MORPH EFFECT
// ============================================================================

function startTextMorph(langCode) {
    const lines = document.querySelectorAll('#morph-text .line');
    const keys = ['motto1', 'motto2', 'motto3'];

    // Phase 1: scramble (0-2s)
    // Phase 2: resolve to target language (2-4s)
    // Phase 3: transition to Midgard (4-5s)

    const scrambleChars = 'ᚠᚢᚦᚨᚱᚲᚷᚹᚻᚾᛁᛃᛇᛈᛉᛊᛏᛒᛖᛗᛚᛝᛟᛞ·.·:';

    lines.forEach((line, idx) => {
        const original = TRANSLATIONS[keys[idx]].la;
        const target = TRANSLATIONS[keys[idx]][langCode] || original;

        // Start scramble after small delay per line
        setTimeout(() => {
            morphLine(line, original, target, scrambleChars);
        }, idx * 300);
    });

    // After morph completes, transition to Midgard
    setTimeout(() => {
        transitionToMidgard(langCode);
    }, 4500);
}

function morphLine(element, from, to, chars) {
    const duration = 2500;
    const frameRate = 50;
    const totalFrames = duration / frameRate;
    let frame = 0;

    const maxLen = Math.max(from.length, to.length);

    const interval = setInterval(() => {
        frame++;
        const progress = frame / totalFrames;

        let result = '';
        for (let i = 0; i < maxLen; i++) {
            if (progress > (i / maxLen) * 0.8 + 0.2) {
                // Resolved character
                result += to[i] || '';
            } else if (progress > (i / maxLen) * 0.3) {
                // Scrambling
                result += chars[Math.floor(Math.random() * chars.length)];
            } else {
                // Original still showing
                result += from[i] || '';
            }
        }

        element.textContent = result;

        if (frame >= totalFrames) {
            clearInterval(interval);
            element.textContent = to;
        }
    }, frameRate);
}

// ============================================================================
// MIDGARD LANDING
// ============================================================================

function transitionToMidgard(langCode) {
    const bifrost = document.getElementById('bifrost');
    const midgard = document.getElementById('midgard');

    // Fade out Bifrost
    bifrost.style.transition = 'opacity 1s ease';
    bifrost.style.opacity = '0';

    setTimeout(() => {
        bifrost.classList.remove('active');
        bifrost.style.opacity = '';

        // Build Midgard content
        document.getElementById('midgard-title').textContent =
            TRANSLATIONS.welcome[langCode] || TRANSLATIONS.welcome.en;
        document.getElementById('midgard-subtitle').textContent =
            TRANSLATIONS.subtitle[langCode] || TRANSLATIONS.subtitle.en;

        const linksContainer = document.getElementById('midgard-links');
        linksContainer.innerHTML = '';
        MIDGARD_LINKS.forEach(link => {
            const a = document.createElement('a');
            a.className = 'midgard-link';
            a.href = link.href;
            a.innerHTML = `<span class="icon">${link.icon}</span><span class="name">${link.name}</span>`;
            linksContainer.appendChild(a);
        });

        // Show Midgard
        midgard.classList.add('active');
    }, 1000);
}
