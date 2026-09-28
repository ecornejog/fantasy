def simulate_tournament(teams):
    """
    Runs one full simulation of the bracket and returns a dict:
        {team_name: placement_label}
    placement_label is one of: "1st", "2nd", "3rd", "4th", "5th-6th", "7th-8th"
    """
    for team in teams:
        team.reset_stats()

    """
    Simulates the whole Swiss stage (ESL Pro League format)

    teams: list of Team objects IN SEED ORDER (index 0 = seed 1), unless you
           pass initial_live_ratings, in which case seeds come from those.
    initial_live_ratings: optional list (same order as `teams`) with ESL's
           baseline ratings (e.g. 1.03, 2.70, ...). Lower = better.
           Default: 1.0, 2.0, ... n (the seed positions).

    Returns:
      standings: list of ALL Team objects, best to worst
                 (wins desc, losses asc, live rating as tiebreak).
                 standings[:8] are the qualified teams, already seeded for
                 the playoffs.
      records:   {team_name: {"wins", "losses", "live_rating"}}
      match_log: list of (round_number, winner_name, loser_name)

    WINS_TO_ADVANCE = 3
    LOSSES_TO_ELIMINATE = 3


    n = len(teams)
    initial_live_ratings = [1.00, 2.33, 3.15, 3.73,4.17,5.45,6.93,7.23,9.00,9.36,9.50,11.00,12.47,13.58,13.69,15.00]

    if initial_live_ratings is None:
        initial_live_ratings = [float(i + 1) for i in range(n)]

    state = {
        team.name: {
            "team": team,
            "live": float(live),
            "wins": 0,
            "losses": 0,
            "opponents": set(),
        }
        for team, live in zip(teams, initial_live_ratings)
    }
    match_log = []

    round_number = 0
    while True:
        active = [
            name for name, s in state.items()
            if s["wins"] < WINS_TO_ADVANCE and s["losses"] < LOSSES_TO_ELIMINATE
        ]
        if not active:
            break
        round_number += 1

        # --- Build this round's matches (all pairings decided BEFORE playing) ---
        if round_number == 1:
            seeded = sorted(active, key=lambda nm: state[nm]["live"])
            matches = [(seeded[i], seeded[-1 - i]) for i in range(len(seeded) // 2)]
        else:
            pools = defaultdict(list)
            for name in active:
                pools[(state[name]["wins"], state[name]["losses"])].append(name)

            matches = []
            for pool in pools.values():
                pool.sort(key=lambda nm: state[nm]["live"])
                matches.extend(pair_pool(pool, state))

        # --- Play the round ---
        for name_a, name_b in matches:
            winner_team, loser_team = play_match(
                state[name_a]["team"], state[name_b]["team"]
            )
            w = state[winner_team.name]
            l = state[loser_team.name]

            w["wins"] += 1
            l["losses"] += 1
            w["opponents"].add(loser_team.name)
            l["opponents"].add(winner_team.name)
            update_live_ratings(w, l)
            match_log.append((round_number, winner_team.name, loser_team.name))

    # --- Final standings ---
    ordered_names = sorted(
        state,
        key=lambda nm: (-state[nm]["wins"], state[nm]["losses"], state[nm]["live"]),
    )
    standings = [state[nm]["team"] for nm in ordered_names]
    records = {
        nm: {
            "wins": state[nm]["wins"],
            "losses": state[nm]["losses"],
            "live_rating": state[nm]["live"],
        }
        for nm in state
    }

    standings[0].padding_rounds = 2
    standings[1].padding_rounds = 2
    standings[2].padding_rounds = 1
    standings[3].padding_rounds = 1
    standings[4].padding_rounds = 1
    standings[11].elim_rounds = 1
    standings[12].elim_rounds = 1
    standings[13].elim_rounds = 1
    standings[14].elim_rounds = 2
    standings[15].elim_rounds = 2
        
    placements = {
        standings[0]: "3-0",
        standings[1]: "3-0",
        standings[2]: "3-1",
        standings[3]: "3-1",
        standings[4]: "3-1",
        standings[5]: "3-2",
        standings[6]: "3-2",
        standings[7]: "3-2",
        standings[8]: "2-3",
        standings[9]: "2-3",
        standings[10]: "2-3",
        standings[11]: "1-3",
        standings[12]: "1-3",
        standings[13]: "1-3",
        standings[14]: "0-3",
        standings[15]: "0-3",
    }
    '''

    '''
    # --- GSL BO3 2 groups ---
    t = teams  # shorthand, list of X team names in seed order
    # --- opening round ---
    ow1A, ol1A = play_match(t[2], t[7])
    ow2A, ol2A = play_match(t[0], t[4])

    ow1B, ol1B = play_match(t[1], t[5])
    ow2B, ol2B = play_match(t[3], t[6])

    # --- winners round ---
    wwA, wlA =  play_match(ow1A, ow2A)
    wwB, wlB =  play_match(ow1B, ow2B)

    wwA.padding_rounds +=1
    wwB.padding_rounds +=1
    
    # --- elimination match ---
    ewA, elA =  play_match(ol1A, ol2A)
    ewB, elB =  play_match(ol1B, ol2B)
    
    elA.elim_rounds = 3
    elB.elim_rounds = 3
    
    # --- decider match ---
    dwA, dlA =  play_match(wlA, ewA)
    dwB, dlB =  play_match(wlB, ewB)

    dlA.elim_rounds = 2
    dlB.elim_rounds = 2
    
    # --- single elimination playoff bracket ---
    # --- Semis ---
    sw1, sl1 = play_match(wwA, dwB)
    sw2, sl2 = play_match(wwB, dwA)

    # ---finals ---
    fw, fl = play_match(sw1, sw2)
    tpdmw, tpdml = play_match(sl1, sl2)

    placements = {
            fw: "1st",
            fl: "2nd",
            tpdmw: "3rd",
            tpdml: "4th",
            dlA: "5th-6th",
            dlB: "5th-6th",
            elA: "7th-8th",
            elB: "7th-8th",
        }
    '''


    '''
    # --- GSL BO3 4 groups ---
    t = teams  # shorthand, list of X team names in seed order
    # --- opening round ---
    ow1A, ol1A = play_match(t[0], t[15])
    ow2A, ol2A = play_match(t[10], t[5])

    ow1B, ol1B = play_match(t[2], t[11])
    ow2B, ol2B = play_match(t[6], t[9])

    ow1C, ol1C = play_match(t[3], t[12])
    ow2C, ol2C = play_match(t[4], t[13])

    ow1D, ol1D = play_match(t[7], t[14])
    ow2D, ol2D = play_match(t[1], t[8])

    # --- winners round ---
    wwA, wlA =  play_match(ow1A, ow2A)
    wwB, wlB =  play_match(ow1B, ow2B)
    wwC, wlC =  play_match(ow1C, ow2C)
    wwD, wlD =  play_match(ow1D, ow2D)

    wwA.padding_rounds +=1
    wwB.padding_rounds +=1
    wwC.padding_rounds +=1
    wwD.padding_rounds +=1

    # --- elimination match ---
    ewA, elA =  play_match(ol1A, ol2A)
    ewB, elB =  play_match(ol1B, ol2B)
    ewC, elC =  play_match(ol1C, ol2C)
    ewD, elD =  play_match(ol1D, ol2D)

    elA.elim_rounds = 4
    elB.elim_rounds = 4
    elC.elim_rounds = 4
    elD.elim_rounds = 4

    # --- decider match ---
    dwA, dlA =  play_match(wlA, ewA)
    dwB, dlB =  play_match(wlB, ewB)
    dwC, dlC =  play_match(wlC, ewC)
    dwD, dlD =  play_match(wlD, ewD)

    dlA.elim_rounds = 3
    dlB.elim_rounds = 3
    dlC.elim_rounds = 3
    dlD.elim_rounds = 3
    
    # --- single elimination playoff bracket ---
    # --- Quarter finals ---
    qw1, ql1 = play_match(wwA,dwD)
    qw2, ql2 = play_match(wwB,dwC)
    qw3, ql3 = play_match(wwC,dwB)
    qw4, ql4 = play_match(wwD,dwA)

    ql1.elim_rounds = 2
    ql2.elim_rounds = 2
    ql3.elim_rounds = 2
    ql4.elim_rounds = 2

    # --- Semis ---
    sw1, sl1 = play_match(qw1, qw2)
    sw2, sl2 = play_match(qw3, qw4)

    sl1.elim_rounds = 1
    sl2.elim_rounds = 1

    # ---finals ---
    fw, fl = play_match(sw1, sw2)

    placements = {
            fw: "1st",
            fl: "2nd",
            sl1: "3rd-4th",
            sl2: "3rd-4th",
            ql1: "5th-8th",
            ql2: "5th-8th",
            ql3: "5th-8th",
            ql4: "5th-8th",
            dlA: "9th-12th",
            dlB: "9th-12th",
            dlC: "9th-12th",
            dlD: "9th-12th",
            elA: "13th-16th",
            elB: "13th-16th",
            elC: "13th-16th",
            elD: "13th-16th",
        }
    '''

    """
    # --- groups round robin ---
    # --- Group Stage ---
    t_G_A = teams[:len(TEAMS_G_A)]
    t_G_B = teams[len(TEAMS_G_A):]

    stats_G_A, match_log_G_A = simulate_group_stage(t_G_A)
    stats_G_B, match_log_G_B = simulate_group_stage(t_G_B)
    standings_G_A = rank_teams(t_G_A, stats_G_A, match_log_G_A)
    standings_G_B = rank_teams(t_G_B, stats_G_B, match_log_G_B)

    for team in standings_G_A:
        team.win_rounds = stats_G_A[team.name]["wins"]
        team.loss_rounds = stats_G_A[team.name]["losses"]
    for team in standings_G_B:
        team.win_rounds = stats_G_B[team.name]["wins"]
        team.loss_rounds = stats_G_B[team.name]["losses"]

    standings_G_A[3].elim_rounds = 3
    standings_G_B[3].elim_rounds = 3
    standings_G_A[4].elim_rounds = 3
    standings_G_B[4].elim_rounds = 3
    standings_G_A[5].elim_rounds = 3
    standings_G_B[5].elim_rounds = 3

    # --- single elimination bracket ---
    # --- quarterfinals ---
    standings_G_A[0].padding_rounds += 1
    standings_G_B[0].padding_rounds += 1
    qf1_w, qf1_l = play_match(standings_G_B[1], standings_G_A[2])
    qf2_w, qf2_l = play_match(standings_G_A[1], standings_G_B[2])
    qf1_l.elim_rounds = 2
    qf2_l.elim_rounds = 2

    # --- semifinals ---
    sf1_w, sf1_l = play_match(standings_G_A[0], qf1_w)
    sf2_w, sf2_l = play_match(standings_G_B[0], qf2_w)
    sf1_l.elim_rounds = 1
    sf2_l.elim_rounds = 1

    # --- finals ---
    f_w, f_l = play_match(sf1_w, sf2_w)
    
    placements = {
        f_w: "1st",
        f_l: "2nd",
        sf1_l: "3rd-4th",
        sf2_l: "3rd-4th",
        qf1_l: "5th-6th",
        qf2_l: "5th-6th",
        standings_G_A[3]: "7th-8th",
        standings_G_B[3]: "7th-8th",
        standings_G_A[4]: "9th-10th",
        standings_G_B[4]: "9th-10th",
        standings_G_A[5]: "11th-12th",
        standings_G_B[5]: "11th-12th",
    }
    """
    '''
    # --- Double elimination bracket structure ---
    t = teams  # shorthand, list of X team names in seed order
    # --- Opening Round ---
    ow1, ol1 = play_match(t[2], t[7])
    ow2, ol2 = play_match(t[4], t[3])
    ow3, ol3 = play_match(t[0], t[6])
    ow4, ol4 = play_match(t[1], t[5])

    # --- Upper Semis ---
    usw1, usl1 = play_match(ow1, ow2)
    usw2, usl2 = play_match(ow3, ow4)

    usw1.padding_rounds += 1
    usw2.padding_rounds += 1

    # --- Upper Final ---
    ufw, ufl = play_match(usw1, usw2)

    ufw.padding_rounds += 1

    # --- Lower Bracket Round 1 (LR1) ---
    lr1w1, lr1l1 = play_match(ol1, ol2)
    lr1w2, lr1l2 = play_match(ol3, ol4)

    lr1l1.elim_rounds = 4 
    lr1l2.elim_rounds = 4 

    # --- Lower Semis (cross-paired to avoid immediate rematches) ---
    lsw1, lsl1 = play_match(lr1w1, usl2)
    lsw2, lsl2 = play_match(lr1w2, usl1)

    lsl1.elim_rounds = 3
    lsl2.elim_rounds = 3

    # --- Lower Final ---
    lfw, lfl = play_match(lsw1, lsw2)

    lfl.elim_rounds = 2

    # --- Cons. Final (3rd place decider) ---
    cfw, cfl = play_match(ufl, lfw)

    cfl.elim_rounds = 1

    # --- Grand Final ---
    gfw, gfl = play_match(ufw, cfw)

    placements = {
        gfw: "1st",
        gfl: "2nd",
        cfl: "3rd",
        lfl: "4th",
        lsl1: "5th-6th",
        lsl2: "5th-6th",
        lr1l1: "7th-8th",
        lr1l2: "7th-8th",
    }
    '''
    return placements
