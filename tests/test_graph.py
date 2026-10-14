"""Kern: Diagramme, d-Separation, Pfade mit Blockierungsgrund, Aussagenmengen, Äquivalenzklassen."""

import pytest

import dsep_graph as G

A, B, C, D = 0, 1, 2, 3


# ----------------------------------------------------------------------------- Aufbau

def test_parents_from_edges_orders_and_deduplicates():
    assert G.parents_from_edges(3, [(1, 2), (0, 2), (0, 1), (0, 2)]) == ((), (0,), (0, 1))
    assert G.edges_of(((), (0,), (0, 1))) == ((0, 1), (0, 2), (1, 2))


@pytest.mark.parametrize("edge", [(1, 0), (2, 2), (0, 5), (-1, 1), (0, 3), (3, 3)])
def test_edges_against_the_topological_order_are_refused(edge):
    with pytest.raises(ValueError):
        G.parents_from_edges(3, [edge])


def test_ancestors_and_descendants_by_hand(mini):
    assert G.ancestors(mini, {D}) == {A, B, C, D}
    assert G.ancestors(mini, {C}) == {A, B, C}
    assert G.ancestors(mini, {A}) == {A}
    assert G.descendants(mini, A) == {C, D}
    assert G.descendants(mini, D) == set()
    assert G.descendants(mini, B) == {C, D}


def test_is_complete():
    assert G.is_complete(((), (0,), (0, 1)))
    assert not G.is_complete(((), (0,), (1,)))
    assert G.is_complete(((),))
    assert G.is_complete(((), (0,)))


# ----------------------------------------------------------------------------- d-Separation an den drei Bausteinen

CHAIN = ((), (0,), (1,))          # 0 -> 1 -> 2
FORK = ((), (0,), (0,))           # 1 <- 0 -> 2
COLLIDER = ((), (), (0, 1))       # 0 -> 2 <- 1


def test_chain_is_open_until_the_middle_is_given():
    assert not G.d_separated(CHAIN, 0, 2, ())
    assert G.d_separated(CHAIN, 0, 2, (1,))


def test_fork_is_open_until_the_common_cause_is_given():
    assert not G.d_separated(FORK, 1, 2, ())
    assert G.d_separated(FORK, 1, 2, (0,))


def test_collider_is_blocked_until_it_is_given():
    assert G.d_separated(COLLIDER, 0, 1, ())
    assert not G.d_separated(COLLIDER, 0, 1, (2,))


def test_descendant_of_a_collider_opens_the_path_too(mini):
    assert G.d_separated(mini, A, B, ())
    assert not G.d_separated(mini, A, B, (C,))
    assert not G.d_separated(mini, A, B, (D,))
    assert not G.d_separated(mini, A, B, (C, D))


def test_mini_instance_has_exactly_the_five_hand_statements(mini):
    expected = {(A, B, ()), (A, D, (C,)), (A, D, (B, C)), (B, D, (C,)), (B, D, (A, C))}
    assert set(G.separations(mini, None)) == expected
    assert not G.d_separated(mini, A, D, (B,)) and not G.d_separated(mini, A, D, ())


def test_mini_instance_local_markov_basis(mini):
    assert G.local_markov_basis(mini) == [(A, B, ()), (A, D, (C,)), (B, D, (C,))]


def test_adjacent_nodes_are_never_separated(mini):
    for z in ((), (A,), (B,), (D,), (B, D)):
        if C not in z and A not in z:
            assert not G.d_separated(mini, A, C, z)


def test_d_separated_refuses_x_in_the_conditioning_set_and_x_equal_y(mini):
    with pytest.raises(ValueError):
        G.d_separated(mini, A, B, (A,))
    with pytest.raises(ValueError):
        G.d_separated(mini, A, A, ())


def test_separations_respect_the_size_cap(mini):
    assert set(G.separations(mini, 1)) == {(A, B, ()), (A, D, (C,)), (B, D, (C,))}
    assert G.separations(mini, 0) == [(A, B, ())]


def test_complete_diagram_has_no_statement():
    complete = ((), (0,), (0, 1), (0, 1, 2))
    assert G.separations(complete, None) == [] and G.local_markov_basis(complete) == []


def test_every_orientation_of_a_complete_triangle_has_no_statement():
    import itertools

    for order in itertools.permutations(range(3)):
        parents = [[] for _ in range(3)]
        for i, a in enumerate(order):
            for b in order[:i]:
                parents[a].append(b)
        assert G.separations(tuple(tuple(p) for p in parents), None) == []


# ----------------------------------------------------------------------------- Pfade und Gründe

def test_paths_of_the_collider_with_descendant_and_their_reasons(mini):
    paths = G.explain_paths(mini, A, B, (C,))
    assert len(paths) == 1 and paths[0].nodes == (A, C, B) and paths[0].arrows == ("→", "←") and not paths[0].blocked
    blocked = G.explain_paths(mini, A, B, ())
    assert blocked[0].blocked and blocked[0].kind == "collider" and blocked[0].blocker == C


def test_path_reason_for_a_chain_names_the_given_node():
    (p,) = G.explain_paths(CHAIN, 0, 2, (1,))
    assert p.blocked and p.kind == "bedingt" and p.blocker == 1 and p.arrows == ("→", "→")


def test_paths_agree_with_the_moralization_on_all_three_node_diagrams():
    import itertools

    for parents in G.all_dags(3):
        for x, y in itertools.combinations(range(3), 2):
            rest = [v for v in range(3) if v not in (x, y)]
            for k in range(len(rest) + 1):
                for z in itertools.combinations(rest, k):
                    via_paths = all(p.blocked for p in G.explain_paths(parents, x, y, z))
                    assert via_paths == G.d_separated(parents, x, y, z), (parents, x, y, z)


def test_the_number_of_paths_is_capped(monkeypatch):
    monkeypatch.setattr(G, "MAX_PATHS", 3)
    dense = ((), (0,), (0, 1), (0, 1, 2), (0, 1, 2, 3))
    assert len(G.explain_paths(dense, 0, 4, ())) == 3


# ----------------------------------------------------------------------------- Äquivalenz

def test_number_of_dags_and_classes_for_three_and_four_nodes():
    assert sum(1 for _ in G.all_dags(3)) == 25 and len(G.equivalence_classes(3)) == 11
    assert sum(1 for _ in G.all_dags(4)) == 543 and len(G.equivalence_classes(4)) == 185


def test_equivalence_classes_by_hand_for_three_nodes():
    classes = G.equivalence_classes(3)
    sizes = sorted(len(v) for v in classes.values())
    assert set(sizes) == {1, 2, 3, 6} and sum(sizes) == 25 and sizes.count(1) == 4
    chain, fork, rev = ((), (0,), (1,)), ((1,), (), (1,)), ((1,), (2,), ())      # 0 -> 1 -> 2, 0 <- 1 -> 2, 0 <- 1 <- 2: Mitte ist Knoten 1
    key = G.statement_set(chain)
    assert key == G.statement_set(fork) == G.statement_set(rev)
    assert G.statement_set(COLLIDER) != key and len(classes[G.statement_set(COLLIDER)]) == 1


def test_all_dags_refuses_more_than_four_nodes():
    with pytest.raises(ValueError):
        list(G.all_dags(5))
