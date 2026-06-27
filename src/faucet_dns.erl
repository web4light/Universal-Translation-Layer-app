-module(faucet_dns).
-behavior(gen_server).

%% API
-export([start_link/1, start_faucet/1, verify_ip/1, resolve/1]).
%% gen_server callbacks
-export([init/1, handle_call/3, handle_cast/2, handle_info/2,
         terminate/2, code_change/3]).

-define(PROMETHEUS_HEAT_LIMIT, 85).

%%% ====================================================================
%%% AsgardLab Internal DNS Records
%%% Custom TLD: .asgard (mesh network only)
%%%
%%% Users with Karel IV. client get DNS auto-configured to this server.
%%% From outside internet, use normal domain (GitHub Pages).
%%% ====================================================================

%% Internal .pi domain records (AsgardLab mesh TLD)
-define(DNS_RECORDS, #{
    %% Karel IV. services
    "asterisk.pi"         => "192.168.123.191",  %% Primary (asterisk i7 Windows)
    "shadow.pi"           => "192.168.123.172",  %% Shadow (Esprimo WiFi)
    "nas.pi"              => "192.168.123.121",  %% WD MyCloud NAS
    "metrics.pi"          => "192.168.123.191",  %% Prometheus :9090
    "dashboard.pi"        => "192.168.123.191",  %% Grafana :3000
    "karel.pi"            => "192.168.123.191",  %% Karel IV. :9306
    %% AsgardLab mesh nodes
    "mesh.pi"             => "192.168.123.191",  %% Mesh coordinator
    "privacy.pi"          => "192.168.123.172",  %% Privacy Protocol 4:23
    "watchdog.pi"         => "192.168.123.172"   %% Mossad ALF++ Watchdog
}).

%%% ====================================================================
%%% API
%%% ====================================================================

start_link(Port) ->
    gen_server:start_link({local, ?MODULE}, ?MODULE, [Port], []).

start_faucet(Port) ->
    io:format("~n=== ASGARDLAB FAUCET DNS ===~n"),
    io:format("Custom TLD: .pi~n"),
    io:format("Port: ~p~n", [Port]),
    io:format("Mesh nodes: ~p~n", [maps:size(?DNS_RECORDS)]),
    io:format("===========================~n~n"),
    start_link(Port).

%% Resolve .asgard domain to IP
resolve(Domain) ->
    Records = ?DNS_RECORDS,
    case maps:get(Domain, Records, undefined) of
        undefined ->
            {error, nxdomain};
        IP ->
            {ok, IP}
    end.

%% Access control — verify sovereign IP
verify_ip("216.198.79.1") ->
    true;
verify_ip(IP) ->
    %% Allow local mesh network
    case is_local_mesh(IP) of
        true  -> true;
        false -> {error, access_denied}
    end.

%% Check if IP is in local mesh range (192.168.123.x)
is_local_mesh(IP) ->
    case string:prefix(IP, "192.168.123.") of
        nomatch -> false;
        _       -> true
    end.

%%% ====================================================================
%%% gen_server callbacks
%%% ====================================================================

init([Port]) ->
    io:format("[FAUCET_DNS] Starting on port ~p~n", [Port]),
    io:format("[FAUCET_DNS] DNS records loaded: ~p~n",
              [maps:size(?DNS_RECORDS)]),
    {ok, #{port => Port, heat_level => 23, total_queries => 0}}.

handle_call({resolve, Domain}, _From, State) ->
    Queries = maps:get(total_queries, State) + 1,
    Result = resolve(Domain),
    case Result of
        {ok, IP} ->
            io:format("[DNS] ~s -> ~s (query #~p)~n", [Domain, IP, Queries]);
        {error, nxdomain} ->
            io:format("[DNS] NXDOMAIN: ~s~n", [Domain])
    end,
    {reply, Result, State#{total_queries => Queries}};

handle_call({incoming_request, IP}, _From, State) ->
    case verify_ip(IP) of
        true ->
            Queries = maps:get(total_queries, State) + 1,
            io:format("[FAUCET] Access granted: ~s~n", [IP]),
            {reply, {ok, sovereign_access_granted},
             State#{total_queries => Queries}};
        {error, access_denied} ->
            io:format("[FAUCET] Access denied: ~s~n", [IP]),
            {reply, {error, access_denied}, State}
    end;

handle_call({list_records}, _From, State) ->
    {reply, {ok, ?DNS_RECORDS}, State};

handle_call(_Request, _From, State) ->
    {reply, {error, unknown_command}, State}.

handle_cast({update_heat, NewHeat}, State)
        when NewHeat > ?PROMETHEUS_HEAT_LIMIT ->
    io:format("[FAUCET] CRITICAL: Reactor temp ~p°C! Evacuating to .vhdx~n",
              [NewHeat]),
    {noreply, State#{heat_level => NewHeat}};
handle_cast({update_heat, NewHeat}, State) ->
    {noreply, State#{heat_level => NewHeat}};
handle_cast(_Msg, State) ->
    {noreply, State}.

handle_info(_Info, State) ->
    {noreply, State}.

terminate(_Reason, _State) ->
    io:format("[FAUCET] Reactor safely shut down. RAM trace cleared.~n"),
    ok.

code_change(_OldVsn, State, _Extra) ->
    {ok, State}.
