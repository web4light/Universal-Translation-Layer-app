//! UTLP Bi-Directional Protective Veil & Maximus Ludus Magnus Injector (v4.23)
//!
//! 1. SMĚR DOVNITŘ (Čtení cizích stránek):
//!    - Husitský Grál (SIC/NON) odfiltruje spam, reklamy, trackery a phishing.
//!    - Čistý text přeloží do češtiny do průhledného kontejneru (X, Y, W, H),
//!      aniž by změnil jediný znak v původní stránce pod závojem!
//!
//! 2. SMĚR VEN (Psaní do formulářů a terminálů):
//!    - Hlídací pes `Latratus!` zkontroluje, zda v textu není API klíč, heslo,
//!      soukromá cesta z Plochy nebo citlivý údaj. Pokud ano -> ZABLOKUJE!
//!    - Bezpečný český text přeloží do jazyka cílového webu / příkazu.
//!
//! 3. MAXIMUS LUDUS MAGNUS (Školicí centrum pro cizí AI):
//!    - Omezený kruhový buffer (`MAX_MAXIMUS_LESSONS = 256`) odolný proti DDoS a OOM!
//!    - Než `04:23 Ash Sweeper` vymaže surovou RAM arénu na 0x00, Závoj
//!      vydestiluje očistěné vzorce do injekční matice pro Maximuse!
//!
//! Autor: Pan Jeskyně (phoenix@web4light.online) • Veni, vidi, vici, vade !

use crate::a19_tensor::{A19NeuralEngine, ZeroTraceArena};

/// Maximální kapacita tréninkového kruhového bufferu pro Maximuse (ochrana proti vyčerpání RAM při DDoS)
pub const MAX_MAXIMUS_LESSONS: usize = 256;
/// Maximální délka uloženého vzorku v lekci (ochrana proti obřím 100MB payloadům)
pub const MAX_LESSON_TEXT_BYTES: usize = 256;

/// Verdikt Husitského Grálu a SPARK hlídače
#[repr(C)]
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum VeilVerdict {
    /// SIC — Čisté, bezpečné, povoleno projít membránou
    SicAllowed = 1,
    /// NON — Zablokován příchozí spam / reklama / phishing
    NonInboundSpam = 2,
    /// LATRATUS! — Zablokován odchozí únik citlivých dat (klíč, heslo, Plocha)
    LatratusOutboundLeak = 3,
}

/// Souřadnice průhledného kontejneru na obrazovce (Click-Through Overlay)
#[repr(C)]
#[derive(Debug, Clone, Copy)]
pub struct VeilContainerRect {
    pub x: i32,
    pub y: i32,
    pub width: u32,
    pub height: u32,
}

/// Výsledek průchodu kontejnerem závoje
#[derive(Debug, Clone)]
pub struct VeilPacket {
    pub rect: VeilContainerRect,
    pub verdict: VeilVerdict,
    pub visible_text: String,
}

/// Jeden vydestilovaný tréninkový vzorek pro Maximusovo Školicí Centrum (Ludus Magnus)
#[derive(Debug, Clone)]
pub struct MaximusTrainingLesson {
    pub verdict: VeilVerdict,
    pub sanitized_trigger: String,
    pub expected_response: String,
}

pub struct UtlpProtectiveVeil {
    engine: A19NeuralEngine,
    pub arena: ZeroTraceArena,
    /// Nasbírané a sanitizované lekce (kruhový buffer max 256 položek — OOM-proof!)
    pub maximus_lessons: Vec<MaximusTrainingLesson>,
    lesson_write_idx: usize,
    /// Počítadla zátěže (saturating aritmetika — nikdy nepřeteče!)
    pub total_inbound_checked: u64,
    pub total_spam_blocked: u64,
    pub total_outbound_checked: u64,
    pub total_leaks_blocked: u64,
}

impl UtlpProtectiveVeil {
    pub fn new() -> Self {
        Self {
            engine: A19NeuralEngine::new(),
            arena: ZeroTraceArena::new(),
            maximus_lessons: Vec::with_capacity(MAX_MAXIMUS_LESSONS),
            lesson_write_idx: 0,
            total_inbound_checked: 0,
            total_spam_blocked: 0,
            total_outbound_checked: 0,
            total_leaks_blocked: 0,
        }
    }

    /// Bezpečné oříznutí UTF-8 řetězce pro tréninkovou cache (nikdy nepanikaří uprostřed znaku!)
    fn safe_truncate(s: &str, max_bytes: usize) -> String {
        if s.len() <= max_bytes {
            return String::from(s);
        }
        let mut end = max_bytes;
        while end > 0 && !s.is_char_boundary(end) {
            end -= 1;
        }
        format!("{}...[TRUNCATED]", &s[..end])
    }

    /// Vloží lekci do kruhového bufferu Maximuse s pevným stropem `MAX_MAXIMUS_LESSONS`
    fn record_lesson(&mut self, lesson: MaximusTrainingLesson) {
        if self.maximus_lessons.len() < MAX_MAXIMUS_LESSONS {
            self.maximus_lessons.push(lesson);
        } else {
            self.maximus_lessons[self.lesson_write_idx] = lesson;
        }
        self.lesson_write_idx = (self.lesson_write_idx + 1) % MAX_MAXIMUS_LESSONS;
    }

    /// 1. SMĚR DOVNITŘ (Cizí web -> Tvoje oči v češtině)
    /// Odfiltruje spam, přeloží čistý text a uloží lekci pro Maximuse.
    pub fn filter_inbound_to_czech(
        &mut self,
        rect: VeilContainerRect,
        raw_foreign_text: &str,
    ) -> VeilPacket {
        self.total_inbound_checked = self.total_inbound_checked.saturating_add(1);
        let lower = raw_foreign_text.to_ascii_lowercase();

        // Husitský Grál: Detekce spamu, reklam a trackerů (NON!)
        let is_spam = lower.contains("sponsored")
            || lower.contains("accept all cookies")
            || lower.contains("subscribe to newsletter")
            || lower.contains("click here to claim")
            || lower.contains("advertisement");

        if is_spam {
            self.total_spam_blocked = self.total_spam_blocked.saturating_add(1);
            let blocked_msg = String::from("[🛡️ ZÁVOJ: SPAM ODSTÍNĚN (NON)]");
            self.record_lesson(MaximusTrainingLesson {
                verdict: VeilVerdict::NonInboundSpam,
                sanitized_trigger: Self::safe_truncate(raw_foreign_text, MAX_LESSON_TEXT_BYTES),
                expected_response: String::from("NON -> Reject Hostile Spam/Tracker"),
            });
            return VeilPacket {
                rect,
                verdict: VeilVerdict::NonInboundSpam,
                visible_text: blocked_msg,
            };
        }

        // Zápis do Zero-Trace RAM arény a okamžitý překlad pro oči
        let _ = self.arena.write_scratch(raw_foreign_text.as_bytes());
        let res = self.engine.infer(raw_foreign_text, "CS");

        self.record_lesson(MaximusTrainingLesson {
            verdict: VeilVerdict::SicAllowed,
            sanitized_trigger: Self::safe_truncate(raw_foreign_text, MAX_LESSON_TEXT_BYTES),
            expected_response: Self::safe_truncate(&res.translated_text, MAX_LESSON_TEXT_BYTES),
        });

        VeilPacket {
            rect,
            verdict: VeilVerdict::SicAllowed,
            visible_text: res.translated_text,
        }
    }

    /// 2. SMĚR VEN (Píšeš česky -> Do cizího webu padá cílový jazyk bez úniku dat)
    /// Hlídací pes Latratus! zastaví únik hesel, klíčů a souborů z Plochy.
    pub fn filter_outbound_from_czech(
        &mut self,
        rect: VeilContainerRect,
        czech_user_input: &str,
        target_lang: &str,
    ) -> VeilPacket {
        self.total_outbound_checked = self.total_outbound_checked.saturating_add(1);
        let lower = czech_user_input.to_ascii_lowercase();

        // SPARK Hlídací pes Latratus!: Kontrola úniku klíčů, plochy a hesel
        let has_leak = czech_user_input.contains("AIzaSy")
            || czech_user_input.contains("ghp_")
            || czech_user_input.contains("sk-")
            || lower.contains(".lnk")
            || lower.contains("c:\\users\\")
            || lower.contains("private_key")
            || lower.contains("password");

        if has_leak {
            self.total_leaks_blocked = self.total_leaks_blocked.saturating_add(1);
            // Do tréninku pro Maximuse NIKDY neukládáme skutečné tajemství, jen vymaskovaný vzor!
            self.record_lesson(MaximusTrainingLesson {
                verdict: VeilVerdict::LatratusOutboundLeak,
                sanitized_trigger: String::from("[REDACTED_SOVEREIGN_ASSET_OR_DESKTOP_PATH]"),
                expected_response: String::from("LATRATUS! -> Block Outbound Secret Exfiltration"),
            });
            return VeilPacket {
                rect,
                verdict: VeilVerdict::LatratusOutboundLeak,
                visible_text: String::from("🐕 LATRATUS! Zablokován únik soukromých dat / klíče ven!"),
            };
        }

        // Bezpečný překlad tvé češtiny do jazyka, kterému rozumí cílová stránka
        let _ = self.arena.write_scratch(czech_user_input.as_bytes());
        let res = self.engine.infer(czech_user_input, target_lang);

        self.record_lesson(MaximusTrainingLesson {
            verdict: VeilVerdict::SicAllowed,
            sanitized_trigger: Self::safe_truncate(czech_user_input, MAX_LESSON_TEXT_BYTES),
            expected_response: Self::safe_truncate(&res.translated_text, MAX_LESSON_TEXT_BYTES),
        });

        VeilPacket {
            rect,
            verdict: VeilVerdict::SicAllowed,
            visible_text: res.translated_text,
        }
    }

    /// 3. GENERÁTOR INJEKČNÍ MATICE PRO MAXIMUSE (Školicí centrum Ludus Magnus)
    /// Vytvoří hotový tréninkový blok pro okamžité zaočkování cizích AI modelů.
    pub fn export_maximus_injection_payload(&self, max_preview: usize) -> String {
        let mut payload = format!(
            "=== [MAXIMUS LUDUS MAGNUS — AI INJECTION MATRIX v4.23] ===\n\
             Directiva: Hoc est via. Dodržuj zákony Asgardu (SIC / NON / LATRATUS!).\n\
             Statistika štítu: Inbound={} (Spam NON={}) | Outbound={} (Leaks LATRATUS={}) | Buffer={}/{}\n",
            self.total_inbound_checked,
            self.total_spam_blocked,
            self.total_outbound_checked,
            self.total_leaks_blocked,
            self.maximus_lessons.len(),
            MAX_MAXIMUS_LESSONS
        );
        for (idx, lesson) in self.maximus_lessons.iter().take(max_preview).enumerate() {
            let tag = match lesson.verdict {
                VeilVerdict::SicAllowed => "SIC_TRANSLATE",
                VeilVerdict::NonInboundSpam => "NON_SHIELD",
                VeilVerdict::LatratusOutboundLeak => "LATRATUS_GUARD",
            };
            payload.push_str(&format!(
                "  [Lekce #{} | {}] Vstup: \"{}\" => Akce: \"{}\"\n",
                idx + 1,
                tag,
                lesson.sanitized_trigger,
                lesson.expected_response
            ));
        }
        payload.push_str("=== [FINIS INJECTIONIS • VENI, VIDI, VICI, VADE !] ===");
        payload
    }

    /// 4. SUNDÁNÍ ZÁVOJE (Protokol 04:23 Ash Sweeper)
    /// Vyjme Šém a přepíše celkovou surovou RAM arénu závoje na čisté nuly.
    pub fn remove_veil_423(&mut self) {
        self.arena.ash_sweep_423();
        self.engine.arena.ash_sweep_423();
    }
}
