-- ============================================================
--  Marketing Engine — Autonomni distribuce a akvizice
--
--  Jak dostat platici lidi BEZ rucniho marketingu:
--    1. Funnel: navstevnik → trial → subscriber → ambassador
--    2. Distribuce: SEO, socialni site, affiliate, word-of-mouth
--    3. Konverze: free tier (znakova rec) → placeny tier
--    4. Retence: metaverse vstup = NFT = loyalty
--
--  Autonomni = zadny clovek nemusi nic delat.
--  System sam meri, sam optimalizuje, sam skali.
--
--  SPARK proved — zadna halucinace v metrikach.
--
--  Autor: Pan Jeskyne
--  Licence: Apache 2.0
-- ============================================================

pragma SPARK_Mode (On);

package Marketing_Engine is

   -- =========================================================
   --  Funnel stages — cesta uzivatele
   -- =========================================================

   type Funnel_Stage is (Visitor,       -- prisel na web
                         Trial,         -- zkusil free tier
                         Subscriber,    -- plati
                         Ambassador);   -- doporucuje dalsi

   -- Cenikove tiery (CZK/mesic)
   type Price_Tier is (Free_Sign,       -- znakova rec ZDARMA
                       Geall_111,       -- 111 CZK
                       Karel_222,       -- 222 CZK
                       Dubbing_333,     -- 333 CZK
                       Family_423);     -- 423 CZK (zakladatel)

   -- Distribucni kanal
   type Channel is (Organic_SEO,        -- vyhledavace
                    Social_X,           -- X/Twitter
                    Social_YouTube,     -- YouTube (dabovane videa)
                    Affiliate,          -- affiliate partneri
                    Word_of_Mouth,      -- doporuceni
                    NFT_Referral,       -- Soulbound NFT bonus
                    Direct);            -- primo web4light.online

   -- =========================================================
   --  Metriky (proved bounds)
   -- =========================================================

   Max_Users    : constant := 9_999_999;
   Max_Revenue  : constant := 999_999_999;  -- halere

   subtype User_Count is Natural range 0 .. Max_Users;
   subtype Revenue is Natural range 0 .. Max_Revenue;

   -- Konverzni pomer (0-100%)
   subtype Conv_Rate is Natural range 0 .. 100;

   -- Stav funnelu
   type Funnel_State is record
      Visitors      : User_Count := 0;
      Trials        : User_Count := 0;
      Subscribers   : User_Count := 0;
      Ambassadors   : User_Count := 0;
      Monthly_Revenue : Revenue := 0;
   end record;

   -- Stav kanalu
   type Channel_Stats is record
      Visitors_From : User_Count := 0;
      Conversions   : User_Count := 0;
      Cost_Halere   : Revenue := 0;  -- kolik stoji kanal
   end record;

   type All_Channels is array (Channel) of Channel_Stats;

   -- Celkovy stav marketingu
   type Marketing_State is record
      Funnel   : Funnel_State;
      Channels : All_Channels;
      Total_Spent : Revenue := 0;
      ROI_Percent : Natural range 0 .. 99_999 := 0;
   end record;

   State : Marketing_State;

   -- =========================================================
   --  Operace
   -- =========================================================

   -- Zaregistrovat noveho navstevnika
   procedure Register_Visitor (Ch : Channel)
     with Global => (In_Out => State),
          Pre    => State.Funnel.Visitors < Max_Users,
          Post   => State.Funnel.Visitors = State.Funnel.Visitors'Old + 1;

   -- Konverze: visitor → trial
   procedure Convert_To_Trial
     with Global => (In_Out => State),
          Pre    => State.Funnel.Trials < Max_Users
                    and State.Funnel.Visitors > 0,
          Post   => State.Funnel.Trials = State.Funnel.Trials'Old + 1;

   -- Konverze: trial → subscriber (plati!)
   procedure Convert_To_Subscriber (Tier : Price_Tier)
     with Global => (In_Out => State),
          Pre    => State.Funnel.Subscribers < Max_Users
                    and State.Funnel.Trials > 0,
          Post   => State.Funnel.Subscribers = State.Funnel.Subscribers'Old + 1;

   -- Konverze: subscriber → ambassador (doporucuje)
   procedure Promote_To_Ambassador
     with Global => (In_Out => State),
          Pre    => State.Funnel.Ambassadors < Max_Users
                    and State.Funnel.Subscribers > 0,
          Post   => State.Funnel.Ambassadors = State.Funnel.Ambassadors'Old + 1;

   -- Spocitej mesicni revenue
   function Calculate_Revenue (Subs : User_Count;
                               Tier : Price_Tier) return Revenue
     with Pre => Subs <= 99_999;

   -- Konverzni pomer visitor→trial
   function Visitor_To_Trial_Rate return Conv_Rate
     with Global => (Input => State);

   -- ROI: (revenue - cost) / cost * 100
   function Calculate_ROI (Rev : Revenue;
                           Cost : Revenue) return Natural
     with Pre  => Cost > 0,
          Post => Calculate_ROI'Result <= 99_999;

end Marketing_Engine;
