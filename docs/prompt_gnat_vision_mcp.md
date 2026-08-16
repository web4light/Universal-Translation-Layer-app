# Prompt pro GNAT Studio — Asgard Vision MCP Server

## Zadání

Vytvoř MCP (Model Context Protocol) server v Ada/SPARK, který:
1. Čte grafické požadavky od klientů (AI agentů) přes stdio JSON-RPC
2. Generuje SVG/HTML grafiku na základě strukturovaného popisu
3. Analyzuje obrázky (předá Gemini multimodal, vrátí textový popis)

## Kontext

Asgard Vision je "oči pro slepé AI agenty". Každý agent (Kiro, Copilot, Grok) je nevidomý — neumí kreslit ani vidět obrázky. Asgard Vision jim dává zrak.

Funguje jako samostatné ministerstvo ve státě Web4Light — autonomní, nezávislé, kooperuje s ostatními přes API.

## Architektura

```
[AI Agent] ←→ stdio JSON-RPC ←→ [Asgard Vision MCP Server (Ada)]
                                        │
                                        ├── read_image (cesta → Gemini → popis)
                                        ├── generate_svg (komponenty + spojení → SVG soubor)
                                        ├── generate_scada (preset Asgard Lab → SVG)
                                        └── describe_scene (VR scéna → text pro nevidomé)
```

## MCP Protocol (JSON-RPC přes stdio)

### Request příklad:
```json
{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"generate_svg","arguments":{"components":[{"id":"server","name":"ASGARD","port":":8000","state":"on"}],"connections":[]}}}
```

### Response příklad:
```json
{"jsonrpc":"2.0","id":1,"result":{"content":[{"type":"text","text":"SVG vygenerován: /tmp/asgard_vision/output.svg"}]}}
```

## Tools (schopnosti serveru)

### 1. generate_svg
- Vstup: pole komponent (id, name, port, value, state) + pole spojení (from, to, color)
- Výstup: SVG soubor ve stylu SCADA/ConWin (průmyslový řídicí panel)
- Styl: zelené pozadí, modré/červené trubky, ventily jako jističe, live hodnoty

### 2. generate_scada
- Vstup: titulek (volitelný)
- Výstup: přednastavený SCADA diagram celého Asgard Lab systému (12 komponent)

### 3. analyze_image
- Vstup: cesta k PNG/JPG souboru
- Výstup: textový popis obrázku (česky)
- Implementace: pošle obrázek jako base64 do Gemini 2.0 Flash multimodal API

### 4. analyze_video
- Vstup: cesta k MP4/WEBM souboru
- Výstup: textový popis videa (co se děje, kdo mluví, co ukazuje, čas)
- Implementace: extrahuje klíčové framy (ffmpeg), pošle do Gemini multimodal
- Použití: VR scény, znakový jazyk rozpoznávání, demo videa

### 5. describe_scene
- Vstup: popis VR scény (objekty, pozice, agenti)
- Výstup: textový popis pro nevidomého agenta (co vidí, kde kdo stojí, co se děje)

## Technické požadavky

### Ada/SPARK část (proved):
- Validace vstupních parametrů (bounds checking)
- SVG generování (template engine s bounded strings)
- JSON parsing (bounded buffers, žádný heap overflow)
- Postconditions: výstup nikdy nepřeteče Max_SVG_Length

### I/O část (pragma SPARK_Mode Off):
- stdio čtení/zápis (JSON-RPC)
- Volání Gemini API (přes curl subprocess)
- Soubor zápis (SVG output)

## Bounded typy (SPARK):

```ada
pragma SPARK_Mode (On);

package Asgard_Vision is
   Max_Components    : constant := 50;
   Max_Connections   : constant := 100;
   Max_SVG_Length    : constant := 65_536;
   Max_Name_Length   : constant := 64;
   Max_Value_Length  : constant := 128;
   Max_Path_Length   : constant := 256;
   
   subtype Component_Count is Natural range 0 .. Max_Components;
   subtype Connection_Count is Natural range 0 .. Max_Connections;
   subtype SVG_Length is Natural range 0 .. Max_SVG_Length;
   
   type Component_State is (On, Off);
   
   type Component is record
      Name     : String (1 .. Max_Name_Length);
      Name_Len : Natural range 0 .. Max_Name_Length := 0;
      Port     : String (1 .. 8);
      Port_Len : Natural range 0 .. 8 := 0;
      Value    : String (1 .. Max_Value_Length);
      Val_Len  : Natural range 0 .. Max_Value_Length := 0;
      State    : Component_State := On;
      X, Y     : Natural range 0 .. 2000 := 0;
      W, H     : Natural range 50 .. 300 := 220;
   end record;
   
   type Connection is record
      From_Idx : Component_Count := 0;
      To_Idx   : Component_Count := 0;
      Hot_Path : Boolean := False;  -- červená vs modrá
   end record;
   
   type Component_Array is array (1 .. Max_Components) of Component;
   type Connection_Array is array (1 .. Max_Connections) of Connection;
   
   type Scene is record
      Components    : Component_Array;
      Comp_Count    : Component_Count := 0;
      Connections   : Connection_Array;
      Conn_Count    : Connection_Count := 0;
   end record;
   
   -- Generuj SVG z Scene
   procedure Generate_SVG (S      : Scene;
                           Output : out String;
                           Length : out SVG_Length)
     with Pre  => S.Comp_Count > 0,
          Post => Length <= Max_SVG_Length;
   
   -- Validuj scénu
   function Is_Valid_Scene (S : Scene) return Boolean
     with Post => Is_Valid_Scene'Result = 
       (S.Comp_Count > 0 and S.Comp_Count <= Max_Components);
   
end Asgard_Vision;
```

## Konfigurace pro klienta (Kiro CLI):

```json
{
  "mcpServers": {
    "asgard-vision": {
      "command": "/home/pj/Universal-Translation-Layer/bin/asgard_vision_server",
      "env": {"GEMINI_API_KEY": "${GEMINI_API_KEY}"}
    }
  }
}
```

## Výstup

- `src/asgard_vision.ads` — SPARK specifikace (proved)
- `src/asgard_vision.adb` — SPARK implementace (proved)
- `src/asgard_vision_server.adb` — I/O wrapper (MCP stdio, pragma SPARK_Mode Off)
- `asgard_vision.gpr` — build projekt
- Po `gprbuild` vznikne `bin/asgard_vision_server`
- ŽÁDNÁ JAVA. Žádný JSON parser v Javě. Čistě Ada.

## Styl SVG výstupu

Referenční obrázek: ConWin řídicí panel (tepelné čerpadlo, zásobníky, ventily).
- Zelené pozadí (#E8F5E9)
- Tmavé bordery (#1B5E20)
- Modré trubky = datový tok (#2196F3)
- Červené trubky = hot path / real-time (#F44336)
- Zelené tečky = ON, červené = OFF
- Trojúhelníkové ventily = jističe
- Monospace font pro hodnoty
- Patička s "SPARK PROVED" stats
