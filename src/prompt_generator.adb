-- ============================================================
--  Prompt Generator — Implementace
--  Ground Truth: pouze ověřená fakta z manifestu Asgard Lab
-- ============================================================
pragma SPARK_Mode (Off);  -- Ada.Text_IO neni SPARK

with Ada.Text_IO; use Ada.Text_IO;

package body Prompt_Generator is

   -- =========================================================
   --  Helper: zkopíruj string do fixed-length bufferu
   -- =========================================================
   procedure Copy (Src : String; Dst : out String; Len : out Natural) is
      L : constant Natural := Natural'Min (Src'Length, Dst'Length);
   begin
      Dst := (others => ' ');
      Dst (Dst'First .. Dst'First + L - 1) := Src (Src'First .. Src'First + L - 1);
      Len := L;
   end Copy;

   -- =========================================================
   --  Prompt 1: Intro Narrative
   -- =========================================================
   function Make_Intro return Prompt_Record is
      P : Prompt_Record;
   begin
      P.Category := Intro_Narrative;
      Copy ("PROMPT 1: Intro Narrative", P.Name, P.Name_Len);
      Copy ("Uvodni predstaveni projektu pro hackathon porotce",
            P.Purpose, P.Purpose_Len);
      Copy ("Ground Truth manifest Asgard Lab", P.Input, P.Input_Len);
      Copy ("3-minutovy uvodni script v anglictine", P.Output, P.Output_Len);
      Copy ("You are Asgard Lab, an autonomous AI translation system " &
            "built by Pan Jeskyne (Rebirth Phoenix Foundation Charter, " &
            "web4light.online). In 30 seconds, introduce yourself to " &
            "hackathon judges. Key facts ONLY: " &
            "1) One architect + AI = power of 50-person team. " &
            "2) Entire pipeline built in one night (Aug 8, 2026). " &
            "3) Principle 1+1=3: Translation + Dubbing = Accessibility. " &
            "4) Ada/SPARK formal verification: mathematical PROOF system " &
            "cannot crash. NOT hope — PROOF. " &
            "5) Sign language FREE for the Deaf (partner: Tichy svet). " &
            "Motto: Loquere lingua tua. Omnes te audient sua lingua. " &
            "Tua voce. No hallucination. Facts only.",
            P.Text, P.Text_Len);
      return P;
   end Make_Intro;

   -- =========================================================
   --  Prompt 2: Technical Demo
   -- =========================================================
   function Make_Technical return Prompt_Record is
      P : Prompt_Record;
   begin
      P.Category := Technical_Demo;
      Copy ("PROMPT 2: Technical Demo", P.Name, P.Name_Len);
      Copy ("Technicka demonstrace pipeline a Ada/SPARK",
            P.Purpose, P.Purpose_Len);
      Copy ("Architektura systemu z manifestu", P.Input, P.Input_Len);
      Copy ("60-sekundovy technicky popis pro inzenyry",
            P.Output, P.Output_Len);
      Copy ("Explain the Asgard Lab technical pipeline to engineers. " &
            "EXACT facts: " &
            "Step 1: User submits YouTube URL. " &
            "Step 2: yt-dlp downloads SRT subtitles (auto-generated). " &
            "Step 3: Groq llama-3.3-70b OR Gemini API translates " &
            "to 22 languages. " &
            "Step 4: gTTS synthesizes dubbed audio synchronized with video. "&
            "Step 5: Sign Language Renderer generates glosses " &
            "(CZJ, ASL, BSL, DGS) FREE. " &
            "Step 6: ffmpeg composites final video. " &
            "Total: ~39 seconds for 60s video (61 subtitles). " &
            "Ada/SPARK core: ranged types prevent buffer overflow, " &
            "pre/postconditions are mathematical contracts, " &
            "bounded loops always terminate, zero memory leaks. " &
            "Infrastructure: RTX 3070 gaming PC + decommissioned server " &
            "+ NAS + 550W solar panel = zero operating costs.",
            P.Text, P.Text_Len);
      return P;
   end Make_Technical;

   -- =========================================================
   --  Prompt 3: Social Impact
   -- =========================================================
   function Make_Social return Prompt_Record is
      P : Prompt_Record;
   begin
      P.Category := Social_Impact;
      Copy ("PROMPT 3: Social Impact", P.Name, P.Name_Len);
      Copy ("Socialni dopad — znakovy jazyk a pristupnost",
            P.Purpose, P.Purpose_Len);
      Copy ("Byznys model a socialni mise", P.Input, P.Input_Len);
      Copy ("45-sekundovy segment o socialni misi",
            P.Output, P.Output_Len);
      Copy ("Describe the social mission of Asgard Lab. " &
            "EXACT facts: " &
            "Agent Mozart generates sign language glosses for the Deaf " &
            "in CZJ (Czech Sign Language), ASL, BSL, DGS — COMPLETELY FREE. "&
            "Partner: Tichy svet (Czech organization for the Deaf). " &
            "Agent Zizka provides audio navigation for the Blind — FREE. " &
            "Business model: PAID = film/series dubbing for families. " &
            "FREE = sign language for Deaf (social mission). " &
            "B2B = API for streaming platforms. " &
            "Real users since August 12, 2026. " &
            "Motto: Finis Fratris Magni. End of Big Brother. " &
            "Protocol 4:23: zero metadata storage.",
            P.Text, P.Text_Len);
      return P;
   end Make_Social;

   -- =========================================================
   --  Prompt 4: Call To Action
   -- =========================================================
   function Make_CTA return Prompt_Record is
      P : Prompt_Record;
   begin
      P.Category := Call_To_Action;
      Copy ("PROMPT 4: Call To Action", P.Name, P.Name_Len);
      Copy ("Vyzva k akci pro porotce a komunitu",
            P.Purpose, P.Purpose_Len);
      Copy ("Hackathon submission a open source info",
            P.Input, P.Input_Len);
      Copy ("30-sekundovy zaver s vyzvaou k akci",
            P.Output, P.Output_Len);
      Copy ("Close the Asgard Lab demo with a call to action. " &
            "EXACT facts: " &
            "Open source: GNU GPLv3 license. " &
            "Repository: github.com/Rebirth-Phoenix-Foundation-Charter/" &
            "Universal-Translation-Layer " &
            "Web: web4light.online " &
            "Contact: phoenix@web4light.online " &
            "Hackathon: All Things Agentic Hackathon 2026, " &
            "track: Taskmaster. " &
            "Organization: Rebirth Phoenix Foundation Charter. " &
            "End with motto: " &
            "Loquere lingua tua. Omnes te audient sua lingua. Tua voce. " &
            "Custos qui non mentitur. Finis Fratris Magni.",
            P.Text, P.Text_Len);
      return P;
   end Make_CTA;

   -- =========================================================
   --  Generate_Suite
   -- =========================================================
   function Generate_Suite return Prompt_Suite is
      S : Prompt_Suite;
   begin
      S (Intro_Narrative) := Make_Intro;
      S (Technical_Demo)  := Make_Technical;
      S (Social_Impact)   := Make_Social;
      S (Call_To_Action)  := Make_CTA;
      return S;
   end Generate_Suite;

   -- =========================================================
   --  Get_Prompt
   -- =========================================================
   function Get_Prompt (Category : Prompt_Category) return Prompt_Record is
      S : constant Prompt_Suite := Generate_Suite;
   begin
      return S (Category);
   end Get_Prompt;

   -- =========================================================
   --  Print_Prompt
   -- =========================================================
   procedure Print_Prompt (P : Prompt_Record) is
   begin
      Put_Line ("-- " & P.Name (1 .. P.Name_Len));
      Put_Line ("-- UCEL:  " & P.Purpose (1 .. P.Purpose_Len));
      Put_Line ("-- VSTUP: " & P.Input (1 .. P.Input_Len));
      Put_Line ("-- VYSTUP:" & P.Output (1 .. P.Output_Len));
      Put_Line ("-- TEXT:");
      Put_Line (P.Text (1 .. P.Text_Len));
      Put_Line ("");
   end Print_Prompt;

   -- =========================================================
   --  Print_Suite
   -- =========================================================
   procedure Print_Suite (S : Prompt_Suite) is
   begin
      Put_Line ("=== ASGARD LAB — PROMPT SUITE PRO DEMO VIDEO ===");
      Put_Line ("=== UTL Protocol 4.23 | web4light.online       ===");
      Put_Line ("");
      for C in Prompt_Category loop
         Print_Prompt (S (C));
      end loop;
      Put_Line ("=== KONEC PROMPT SUITE ===");
   end Print_Suite;

   -- =========================================================
   --  Prompt_Char_Count
   -- =========================================================
   function Prompt_Char_Count (P : Prompt_Record) return Prompt_Length is
   begin
      return P.Text_Len;
   end Prompt_Char_Count;

end Prompt_Generator;
