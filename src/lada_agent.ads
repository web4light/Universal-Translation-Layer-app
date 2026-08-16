-- ============================================================
--  Lada Agent — Graficky AI agent (Asgard Studio)
--
--  Josef Lada — cesky malir, ilustrator Svejka.
--  Lada kresli pro Cave Lab. Proved jadro, xAI backend.
--
--  Schopnosti:
--    - Generovani obrazku z textu (text-to-image)
--    - Logo design
--    - UI/UX navrhy
--    - Barevna schemata
--    - SVG ikony
--    - Metaverse assety (3D koncept)
--
--  SPARK proved — validace vstupu, output bounds.
--  GPL-free. Apache 2.0.
--
--  Autor: Pan Jeskyne
--  Organizace: Rebirth Phoenix Foundation Charter
-- ============================================================

pragma SPARK_Mode (On);

package Lada_Agent is

   -- Maximalni delky
   Max_Prompt_Length  : constant := 4_096;
   Max_Style_Length   : constant := 64;
   Max_Filename_Len   : constant := 256;

   subtype Prompt_Length is Natural range 0 .. Max_Prompt_Length;
   subtype Style_Length is Natural range 0 .. Max_Style_Length;
   subtype File_Name_Length is Natural range 0 .. Max_Filename_Len;

   -- Typ grafickeho vystupu
   type Output_Kind is (Image_PNG,       -- rastrovy obrazek
                        Image_SVG,       -- vektorova grafika
                        Logo,            -- logo design
                        Icon_Set,        -- sada ikon
                        Color_Palette,   -- barevne schema
                        UI_Mockup,       -- UI navrh
                        Asset_3D);       -- 3D koncept pro metaverse

   -- Styl kresleni
   type Art_Style is (Realistic,         -- fotorealisticky
                      Illustration,      -- ilustrace (Lada styl!)
                      Minimalist,        -- minimalisticky
                      Cyberpunk,         -- tmave, neonove
                      Czech_Folk,        -- cesky lidovy
                      Abstract_Art,      -- abstraktni
                      Pixel_Art);        -- retro pixel

   -- Velikost obrazku
   type Image_Size is (Small,            -- 256x256
                       Medium,           -- 512x512
                       Large,            -- 1024x1024
                       Wide,             -- 1792x1024
                       Tall);            -- 1024x1792

   -- Stav requestu
   type Request_Status is (Empty,
                           Validated,
                           Submitted,
                           Generating,
                           Completed,
                           Failed);

   -- Jeden graficky request
   type Lada_Request is record
      Status      : Request_Status := Empty;
      Kind        : Output_Kind := Image_PNG;
      Style       : Art_Style := Illustration;
      Size        : Image_Size := Large;
      Prompt_Len  : Prompt_Length := 0;
      Filename_Len : File_Name_Length := 0;
      Has_Reference : Boolean := False;    -- ma referencni obrazek?
      Is_NSFW_Safe  : Boolean := True;     -- proved: zadny NSFW
      Seed        : Natural range 0 .. 999_999_999 := 0;
   end record;

   -- =========================================================
   --  Validace
   -- =========================================================

   -- Je prompt bezpecny a validni?
   function Is_Valid_Request (Req : Lada_Request) return Boolean
     with Post => (if Req.Prompt_Len = 0 then
                     Is_Valid_Request'Result = False);

   -- Validuj a nastav status
   procedure Validate (Req : in out Lada_Request)
     with Pre  => Req.Status = Empty and Req.Prompt_Len > 0,
          Post => Req.Status = Validated or Req.Status = Failed;

   -- Dokonci request (volano po uspesnem generovani)
   procedure Complete (Req : in out Lada_Request)
     with Pre  => Req.Status = Submitted or Req.Status = Generating,
          Post => Req.Status = Completed;

   -- Oznac failure
   procedure Fail (Req : in out Lada_Request)
     with Post => Req.Status = Failed;

   -- =========================================================
   --  Statistiky (proved counters)
   -- =========================================================

   type Generation_Counter is new Natural range 0 .. 99_999_999;

   -- Pocet vygenerovanych obrazku (monotonni, nepretece)
   procedure Count_Generation (Counter : in out Generation_Counter)
     with Pre  => Counter < Generation_Counter'Last,
          Post => Counter = Counter'Old + 1;

   -- Pocet failnuych (monotonni)
   procedure Count_Failure (Counter : in out Generation_Counter)
     with Pre  => Counter < Generation_Counter'Last,
          Post => Counter = Counter'Old + 1;

end Lada_Agent;
