-- ============================================================
--  Marketing Engine — Implementation
--  "Lidi plati kdyz vidi hodnotu. Ne kdyz vidi reklamu."
-- ============================================================

pragma SPARK_Mode (On);

package body Marketing_Engine is

   -- Cenik v halerech
   function Tier_Price (Tier : Price_Tier) return Natural is
   begin
      case Tier is
         when Free_Sign   => return 0;       -- ZDARMA navzdy
         when Geall_111   => return 11_100;  -- 111 CZK
         when Karel_222   => return 22_200;  -- 222 CZK
         when Dubbing_333 => return 33_300;  -- 333 CZK
         when Family_423  => return 42_300;  -- 423 CZK
      end case;
   end Tier_Price;

   -- =========================================================
   --  Register_Visitor
   -- =========================================================

   procedure Register_Visitor (Ch : Channel) is
   begin
      State.Funnel.Visitors := State.Funnel.Visitors + 1;
      if State.Channels (Ch).Visitors_From < Max_Users then
         State.Channels (Ch).Visitors_From :=
           State.Channels (Ch).Visitors_From + 1;
      end if;
   end Register_Visitor;

   -- =========================================================
   --  Convert_To_Trial
   -- =========================================================

   procedure Convert_To_Trial is
   begin
      State.Funnel.Trials := State.Funnel.Trials + 1;
   end Convert_To_Trial;

   -- =========================================================
   --  Convert_To_Subscriber
   -- =========================================================

   procedure Convert_To_Subscriber (Tier : Price_Tier) is
      Price : constant Natural := Tier_Price (Tier);
   begin
      State.Funnel.Subscribers := State.Funnel.Subscribers + 1;

      -- Pridej mesicni revenue
      if State.Funnel.Monthly_Revenue <= Max_Revenue - Price then
         State.Funnel.Monthly_Revenue :=
           State.Funnel.Monthly_Revenue + Price;
      end if;
   end Convert_To_Subscriber;

   -- =========================================================
   --  Promote_To_Ambassador
   -- =========================================================

   procedure Promote_To_Ambassador is
   begin
      State.Funnel.Ambassadors := State.Funnel.Ambassadors + 1;
   end Promote_To_Ambassador;

   -- =========================================================
   --  Calculate_Revenue
   -- =========================================================

   function Calculate_Revenue (Subs : User_Count;
                               Tier : Price_Tier) return Revenue is
      Price : constant Natural := Tier_Price (Tier);
      Result_Val : Natural;
   begin
      if Subs > 0 and then Price > Max_Revenue / Subs then
         return Max_Revenue;
      end if;
      Result_Val := Subs * Price;
      if Result_Val > Max_Revenue then
         return Max_Revenue;
      end if;
      return Result_Val;
   end Calculate_Revenue;

   -- =========================================================
   --  Visitor_To_Trial_Rate
   -- =========================================================

   function Visitor_To_Trial_Rate return Conv_Rate is
      Rate : Natural;
   begin
      if State.Funnel.Visitors = 0 then
         return 0;
      end if;
      if State.Funnel.Trials > State.Funnel.Visitors then
         return 100;
      end if;
      Rate := State.Funnel.Trials * 100 / State.Funnel.Visitors;
      if Rate > 100 then
         return 100;
      end if;
      return Rate;
   end Visitor_To_Trial_Rate;

   -- =========================================================
   --  Calculate_ROI
   -- =========================================================

   function Calculate_ROI (Rev : Revenue;
                           Cost : Revenue) return Natural is
      Profit : Natural;
      ROI : Natural;
   begin
      if Rev <= Cost then
         return 0;
      end if;
      Profit := Rev - Cost;
      if Profit > Max_Revenue / 100 then
         return 99_999;
      end if;
      ROI := Profit * 100 / Cost;
      if ROI > 99_999 then
         return 99_999;
      end if;
      return ROI;
   end Calculate_ROI;

end Marketing_Engine;
