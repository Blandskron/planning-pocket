"""End-to-end tests for the table, driven through a real browser.

Scope, and why it is drawn here:

The room is served by a normal Django view, so `live_server` (WSGI) renders it
faithfully and the stylesheet loads — which is what makes assertions about real
geometry possible. What WSGI cannot give us is a WebSocket, so these tests split
the work in two:

- Everything that happens on load is exercised for real: seats placed on the ring,
  the fan, identity, the felt's counter, accessibility, the empty state.
- The choreography that a broadcast normally triggers (reveal, a throw, the recess)
  is driven by calling the client's own functions, because what needs protecting is
  the choreography, not the dispatch.

`live_server` is asked for before `page` on purpose: it pulls in the database
fixtures, so the test database is built before Playwright's dispatcher loop exists.
The other way round, Django sees a running loop and refuses every sync query. The
alternative was DJANGO_ALLOW_ASYNC_UNSAFE, which would have blinded the same check
across the consumer tests, where it is worth keeping.

The dispatch itself — that a `room.revealed` or `player.hit` message reaches those
functions — is covered by the consumer tests in `test_websockets.py`.
"""

import pytest

from rooms.models import Issue, Participant, PokerRoom

pytestmark = [pytest.mark.e2e, pytest.mark.django_db(transaction=True)]

PASSWORD = "table-pass-12345"


@pytest.fixture
def table(django_user_model):
    """A room, its facilitator, and a factory for filling the other seats."""

    owner = django_user_model.objects.create_user(username="facilitator", password=PASSWORD)
    room = PokerRoom.objects.create(owner=owner, name="Refinamiento")
    me = Participant.objects.create(
        room=room, user=owner, display_name="facilitator", connection_count=1
    )

    def seat(count, votes=None):
        """Add `count` guests, optionally with votes, and return them."""
        names = ["Ana", "Bruno", "Carla", "Diego", "Elena", "Fabio",
                 "Gina", "Hugo", "Iris", "Jon", "Kira", "Leo", "Mara", "Nil", "Olga"]
        pets = ["gato", "perro", "axolote", "capibara", "dragon", "rana"]
        guests = []
        for index in range(count):
            guests.append(Participant.objects.create(
                room=room,
                display_name=names[index % len(names)] + ("" if index < len(names) else str(index)),
                pet=pets[index % len(pets)],
                color_index=index % 7,
                connection_count=1,
                current_vote=(votes[index] if votes and index < len(votes) else None),
            ))
        return guests

    return {"owner": owner, "room": room, "me": me, "seat": seat}


def enter_room(live_server, page, table, width=1440, height=900):
    """Sign in as the facilitator and open the room."""
    page.set_viewport_size({"width": width, "height": height})
    page.goto(f"{live_server.url}/accounts/login/")
    page.fill("[name=username]", "facilitator")
    page.fill("[name=password]", PASSWORD)
    page.click("main form button[type=submit]")
    page.goto(f"{live_server.url}/p/{table['room'].public_id}/")
    page.wait_for_selector(".table-seat")
    # layoutSeats() runs at the end of the inline script; wait for its output.
    page.wait_for_function(
        "() => document.querySelector('.table-seat')"
        ".style.getPropertyValue('--seat-angle') !== ''"
    )


# --------------------------------------------------------------------------- #
# The ring. This is the regression that phase 1 existed to fix: seats used to be
# pinned to eight hardcoded positions and the ninth broke the layout.
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("people", [2, 3, 5, 8, 9, 12, 14])
def test_the_ring_never_overlaps_or_leaves_the_stage(live_server, page, table, people):
    table["seat"](people - 1)
    enter_room(live_server, page, table)

    report = page.evaluate("""() => {
        const stage = document.getElementById('table-stage').getBoundingClientRect();
        const seats = [...document.querySelectorAll('.table-seat')];
        const boxes = seats.map(s => s.getBoundingClientRect());
        let overlaps = 0;
        for (let i = 0; i < boxes.length; i++)
            for (let j = i + 1; j < boxes.length; j++) {
                const a = boxes[i], b = boxes[j];
                if (a.left < b.right && b.left < a.right &&
                    a.top < b.bottom && b.top < a.bottom) overlaps++;
            }
        const outside = boxes.filter(b =>
            b.left < stage.left - 3 || b.right > stage.right + 3 ||
            b.top < stage.top - 3 || b.bottom > stage.bottom + 3).length;
        return {count: boxes.length, overlaps, outside};
    }""")

    assert report["count"] == people
    assert report["overlaps"] == 0, f"{report['overlaps']} seats overlap with {people} people"
    assert report["outside"] == 0, f"{report['outside']} seats fall outside the stage"


def test_everyone_sees_their_own_seat_at_the_front(live_server, page, table):
    table["seat"](6)
    enter_room(live_server, page, table)

    assert page.evaluate("""() => {
        const boxes = [...document.querySelectorAll('.table-seat')].map(s => ({
            mine: s.classList.contains('is-me'), top: s.getBoundingClientRect().top}));
        const lowest = Math.max(...boxes.map(b => b.top));
        return Math.abs(boxes.find(b => b.mine).top - lowest) < 3;
    }""")


def test_seats_are_spread_around_the_whole_ring(live_server, page, table):
    """Equal-angle placement used to bunch seats into one quadrant on small tables."""
    table["seat"](3)
    enter_room(live_server, page, table)

    spread = page.evaluate("""() => {
        const stage = document.getElementById('table-stage').getBoundingClientRect();
        const centres = [...document.querySelectorAll('.table-seat')].map(s => {
            const b = s.getBoundingClientRect();
            return {x: b.left + b.width / 2 - stage.left, y: b.top + b.height / 2 - stage.top};
        });
        const xs = centres.map(c => c.x), ys = centres.map(c => c.y);
        return {
            widthUsed: (Math.max(...xs) - Math.min(...xs)) / stage.width,
            heightUsed: (Math.max(...ys) - Math.min(...ys)) / stage.height
        };
    }""")
    assert spread["widthUsed"] > 0.5, "four seats should not huddle horizontally"
    assert spread["heightUsed"] > 0.4, "four seats should not huddle vertically"


# --------------------------------------------------------------------------- #
# The hand and the felt
# --------------------------------------------------------------------------- #

def test_the_deck_is_a_fan_not_a_row(live_server, page, table):
    enter_room(live_server, page, table)

    fan = page.evaluate("""() => {
        const cards = [...document.querySelectorAll('.poker-card')];
        return {
            count: cards.length,
            distinctTransforms: new Set(cards.map(c => getComputedStyle(c).transform)).size,
            overlapping: cards.length > 1 &&
                cards[1].getBoundingClientRect().left <
                cards[0].getBoundingClientRect().right
        };
    }""")
    assert fan["count"] == 13
    assert fan["distinctTransforms"] > 1, "every card carries the same rotation: the fan is flat"
    assert fan["overlapping"], "cards do not overlap: this is a row, not a hand"


def test_the_felt_counts_the_votes_placed(live_server, page, table):
    table["seat"](4, votes=["8", "5", None, "8"])
    enter_room(live_server, page, table)

    assert page.text_content("#table-tally") == "3 de 5 han votado"
    assert page.eval_on_selector("#table-pile", "el => el.children.length") == 3


def test_the_monogram_is_gone_from_the_felt(live_server, page, table):
    """The centre reports the round now; it used to be a static 'PP'."""
    enter_room(live_server, page, table)
    assert page.locator(".table-monogram").count() == 0
    assert page.locator(".table-marks").count() == 1


# --------------------------------------------------------------------------- #
# Identity
# --------------------------------------------------------------------------- #

def test_every_seat_is_drawn_with_its_own_pet_and_colour(live_server, page, table):
    table["seat"](6)
    enter_room(live_server, page, table)

    identity = page.evaluate("""() => {
        const seats = [...document.querySelectorAll('.table-seat')];
        return {
            petsDrawn: seats.every(
                s => s.querySelector('.seat-pet').getBoundingClientRect().width > 5),
            petsWired: seats.every(
                s => (s.querySelector('.seat-pet use').getAttribute('href') || '')
                    .startsWith('#pet-')),
            facesWired: seats.every(
                s => (s.querySelector('.seat-avatar use').getAttribute('href') || '')
                    .startsWith('#face-')),
            distinctColours: new Set(seats.map(
                s => getComputedStyle(s.querySelector('.seat-avatar')).backgroundColor)).size,
            spriteSymbols: document.querySelectorAll('.table-sprite symbol').length
        };
    }""")
    assert identity["petsDrawn"] and identity["petsWired"] and identity["facesWired"]
    assert identity["distinctColours"] >= 6
    assert identity["spriteSymbols"] >= 15


def test_only_other_people_are_aim_targets(live_server, page, table):
    table["seat"](4)
    enter_room(live_server, page, table)

    aim = page.evaluate("""() => {
      const aim = '.seat-avatar[data-throw-target]';
      return {
        targets: document.querySelectorAll(aim).length,
        myAvatarIsNotATarget: !document.querySelector('.table-seat.is-me .seat-avatar')
            .hasAttribute('data-throw-target'),
        allTargetsAreButtons: [...document.querySelectorAll(aim)]
            .every(b => b.tagName === 'BUTTON'),
        allTargetsLabelled: [...document.querySelectorAll(aim)]
            .every(b => !!b.getAttribute('aria-label')),
        nestedButtons: document.querySelectorAll('button button').length
      };
    }""")
    assert aim["targets"] == 4
    assert aim["myAvatarIsNotATarget"]
    assert aim["allTargetsAreButtons"] and aim["allTargetsLabelled"]
    assert aim["nestedButtons"] == 0, "an interactive control ended up inside another one"


# --------------------------------------------------------------------------- #
# The reveal, which is the emotional peak and had the least choreography
# --------------------------------------------------------------------------- #

def test_the_reveal_counts_down_then_turns_the_cards_one_by_one(live_server, page, table):
    table["seat"](5, votes=["8", "5", "8", "13", "8"])
    issue = Issue.objects.create(room=table["room"], title="Migrar OIDC")
    table["room"].active_issue = issue
    table["room"].save(update_fields=["active_issue"])
    enter_room(live_server, page, table)

    page.evaluate("""() => {
        const participants = [...document.querySelectorAll('.table-seat')].map((seat, index) => ({
            id: Number(seat.dataset.participantId),
            display_name: 'x',
            has_voted: index > 0,
            is_online: true,
            current_vote: index > 0 ? ['8', '5', '8', '13', '8'][index - 1] : null
        }));
        window.__revealed = participants.filter(p => p.has_voted).length;
        playReveal(participants,
            {vote_count: 5, numeric_vote_count: 5, average: 8.4, has_consensus: false});
    }""")

    # the countdown holds the cards face down for a beat
    page.wait_for_function("() => document.getElementById('table-count').textContent !== ''")
    assert page.locator(".table-seat.is-revealed").count() == 0, (
        "cards turned before the countdown finished"
    )

    page.wait_for_function(
        "() => document.querySelectorAll('.table-seat.is-revealed').length === 6", timeout=8000
    )
    page.wait_for_selector("#round-result:not([hidden])")

    result = page.evaluate("""() => ({
        average: document.getElementById('result-average').textContent,
        range: document.getElementById('result-range').textContent,
        votes: document.getElementById('result-count').textContent,
        verdict: document.getElementById('result-verdict').textContent,
        verdictClass: document.getElementById('result-verdict').className,
        bars: [...document.querySelectorAll('.result-bar')]
            .map(b => b.querySelector('span').textContent),
        edges: [...document.querySelectorAll('.result-bar.is-edge')]
            .map(b => b.querySelector('span').textContent),
        countdownCleared: document.getElementById('table-count').textContent === ''
    })""")

    assert result["average"] == "8.4", "the average reached the table unrounded"
    assert result["range"] == "5–13"
    assert result["votes"] == "5"
    assert result["verdict"] == "Sin consenso"
    assert "is-split" in result["verdictClass"]
    assert result["bars"] == ["5", "8", "13"]
    assert set(result["edges"]) == {"5", "13"}, "a split table must show where it split"
    assert result["countdownCleared"]


def test_unanimity_lights_the_felt(live_server, page, table):
    table["seat"](3, votes=["8", "8", "8"])
    enter_room(live_server, page, table)

    page.evaluate("""() => {
        const participants = [...document.querySelectorAll('.table-seat')].map((seat, index) => ({
            id: Number(seat.dataset.participantId), display_name: 'x',
            has_voted: index > 0, is_online: true, current_vote: index > 0 ? '8' : null
        }));
        playReveal(participants,
            {vote_count: 3, numeric_vote_count: 3, average: 8.0, has_consensus: true});
    }""")

    page.wait_for_selector("#round-result:not([hidden])", timeout=8000)
    outcome = page.evaluate("""() => ({
        verdict: document.getElementById('result-verdict').textContent,
        verdictClass: document.getElementById('result-verdict').className,
        glowed: document.getElementById('table-stage').classList.contains('is-consensus'),
        edges: document.querySelectorAll('.result-bar.is-edge').length
    })""")
    assert outcome["verdict"] == "Consenso"
    assert "is-consensus" in outcome["verdictClass"]
    assert outcome["glowed"], "unanimity did not light the felt"
    assert outcome["edges"] == 0, "there are no outliers when everyone agrees"


# --------------------------------------------------------------------------- #
# The playful layer
# --------------------------------------------------------------------------- #

def test_a_thrown_object_lands_and_clears_the_felt_afterwards(live_server, page, table):
    guests = table["seat"](3)
    enter_room(live_server, page, table)

    page.evaluate(
        "target => playThrow(myParticipantId, target, 'tomate')", guests[0].id
    )
    page.wait_for_selector(".throw-decal", timeout=8000)

    landed = page.evaluate("""() => ({
        decals: document.querySelectorAll('.throw-decal').length,
        label: (document.querySelector('.throw-label') || {}).textContent,
        hitSeat: !!document.querySelector('.table-seat.is-hit'),
        decalOnALayerBelowTheSeats: getComputedStyle(document.querySelector('.throw-decal')).zIndex
            < getComputedStyle(document.querySelector('.table-seats')).zIndex
    })""")
    assert landed["decals"] == 1
    assert landed["label"] == "Tomate"
    assert landed["hitSeat"]
    assert landed["decalOnALayerBelowTheSeats"]

    # nothing may be left on the felt, or a busy table turns to soup
    page.wait_for_function(
        "() => document.querySelectorAll('.throw-decal').length === 0", timeout=8000
    )
    assert page.locator(".throw-fly").count() == 0
    assert page.locator(".throw-label").count() == 0
    assert page.locator(".table-seat.is-hit").count() == 0


def test_turning_the_layer_off_removes_the_tray_and_the_targets(live_server, page, table):
    table["seat"](3)
    enter_room(live_server, page, table)

    assert page.locator("#throw-tray").is_visible()
    page.evaluate("() => { allowPlayful = false; syncThrowTargets(); }")
    off = page.evaluate("""() => ({
        trayHidden: document.getElementById('throw-tray').hidden,
        targetsDisabled: [...document.querySelectorAll('.seat-avatar[data-throw-target]')]
            .every(b => b.disabled)
    })""")
    assert off["trayHidden"], "the tray stayed visible, inviting clicks that will be refused"
    assert off["targetsDisabled"]


def test_effects_off_stops_drawing_without_stopping_the_room(live_server, page, table):
    guests = table["seat"](3)
    enter_room(live_server, page, table)

    page.evaluate("() => setEffects(false)")
    page.evaluate("target => playThrow(myParticipantId, target, 'tomate')", guests[0].id)
    page.wait_for_timeout(900)

    assert page.locator(".throw-decal").count() == 0
    assert page.locator(".throw-fly").count() == 0
    assert page.locator(".table-seat.is-hit").count() == 0
    assert page.locator(".table-seat").count() == 4, "the table itself must be untouched"


# --------------------------------------------------------------------------- #
# The recess
# --------------------------------------------------------------------------- #

def test_the_recess_sits_over_the_table_without_taking_the_hand_away(live_server, page, table):
    table["seat"](4)
    enter_room(live_server, page, table)

    page.evaluate("() => applyRecess(true)")
    page.wait_for_selector(".recess-walker", timeout=8000)

    recess = page.evaluate("""() => {
        const layer = document.getElementById('recess-layer').getBoundingClientRect();
        const walkers = [...document.querySelectorAll('.recess-walker')];
        return {
            walkers: walkers.length,
            spots: [...document.querySelectorAll('.recess-spot b')].map(b => b.textContent),
            allInsideTheFloor: walkers.every(w => {
                const r = w.getBoundingClientRect();
                return r.left >= layer.left - 25 && r.right <= layer.right + 25;
            }),
            movedByTransform: walkers.every(w => w.style.transform.startsWith('translate(')),
            seatsStillVisible: Number(
                getComputedStyle(document.getElementById('participants-list')).opacity) > 0.2,
            handStillUsable: [...document.querySelectorAll('.poker-card')].every(c => !c.disabled),
            handNotCovered: (() => {
                const deck = document.getElementById('deck').getBoundingClientRect();
                return deck.top >= layer.bottom - 1;
            })()
        };
    }""")

    assert recess["walkers"] == 5
    assert recess["spots"] == ["Cafetera", "Dispensador", "Pizarra", "Ventana"]
    assert recess["allInsideTheFloor"]
    assert recess["movedByTransform"], "walkers moved with layout properties instead of transform"
    assert recess["seatsStillVisible"], "the recess hid who had voted"
    assert recess["handStillUsable"] and recess["handNotCovered"], (
        "you must be able to vote while walking"
    )


def test_standing_at_the_coffee_machine_is_written_as_text(live_server, page, table):
    table["seat"](3)
    enter_room(live_server, page, table)
    page.evaluate("() => applyRecess(true)")
    page.wait_for_selector(".recess-walker")

    before = page.text_content("#state-status-%d" % table["me"].id)
    page.evaluate("""() => {
        const me = walkers.get(myParticipantId);
        me.x = 0.11; me.y = 0.2; me.tx = me.x; me.ty = me.y;
        drawWalkers(); updateProximity();
    }""")
    assert page.text_content("#state-status-%d" % table["me"].id) == "En pausa"
    assert page.locator(".recess-spot[data-spot=cafetera].is-near").count() == 1

    page.evaluate("""() => {
        const me = walkers.get(myParticipantId);
        me.x = 0.5; me.y = 0.5; me.tx = me.x; me.ty = me.y;
        drawWalkers(); updateProximity();
    }""")
    assert page.text_content("#state-status-%d" % table["me"].id) == before, "the pause label stuck"


def test_closing_the_recess_puts_everyone_back_in_their_seat(live_server, page, table):
    table["seat"](3)
    enter_room(live_server, page, table)
    page.evaluate("() => applyRecess(true)")
    page.wait_for_selector(".recess-walker")

    page.evaluate("() => applyRecess(false)")
    page.wait_for_function(
        "() => document.querySelectorAll('.recess-walker').length === 0", timeout=8000
    )
    assert not page.locator("#table-stage.is-recess").count()
    assert page.locator(".recess-spot").count() == 0


# --------------------------------------------------------------------------- #
# States that used to look broken, and accessibility
# --------------------------------------------------------------------------- #

def test_one_person_at_the_table_is_a_normal_state(live_server, page, table):
    enter_room(live_server, page, table)

    alone = page.evaluate("""() => ({
        marked: document.getElementById('table-stage').classList.contains('is-alone'),
        message: document.querySelector('.table-empty strong').textContent,
        emptyShown: document.getElementById('table-empty').checkVisibility(),
        marksHidden: getComputedStyle(document.querySelector('.table-marks')).display === 'none'
    })""")
    assert alone["marked"] and alone["emptyShown"] and alone["marksHidden"]
    assert "mascota" in alone["message"]


def test_the_sidebar_no_longer_dictates_the_height_of_the_page(live_server, page, table):
    enter_room(live_server, page, table)

    sidebar = page.evaluate("""() => {
        const el = document.getElementById('room-sidebar');
        const open = el.getBoundingClientRect().height;
        el.open = false;
        const closed = el.getBoundingClientRect().height;
        el.open = true;
        return {tag: el.tagName, minHeight: getComputedStyle(el).minHeight, open, closed};
    }""")
    assert sidebar["tag"] == "DETAILS"
    assert sidebar["minHeight"] == "auto", "the fixed min-height is back"
    assert sidebar["closed"] < 140, "collapsing the sidebar did not free the space"


def test_state_is_never_only_colour_and_decoration_is_never_announced(live_server, page, table):
    table["seat"](4, votes=["8", None, "5", None])
    enter_room(live_server, page, table)

    a11y = page.evaluate("""() => ({
        decorationHidden: ['.table-oval', '#table-glow', '#table-pile',
                           '#table-count', '.table-sprite']
            .every(s => document.querySelector(s).getAttribute('aria-hidden') === 'true'),
        tallyAnnounced:
            document.getElementById('table-tally').getAttribute('aria-live') === 'polite' &&
            document.getElementById('table-tally').getAttribute('aria-hidden') === null,
        seatsAnnounced:
            document.getElementById('participants-list').getAttribute('aria-live') === 'polite',
        everyStateIsText: [...document.querySelectorAll('.seat-state')]
            .every(s => s.textContent.trim().length > 0),
        states: [...document.querySelectorAll('.seat-state')].map(s => s.textContent.trim()),
        cardsLabelled: [...document.querySelectorAll('.poker-card')]
            .every(c => !!c.getAttribute('aria-label')),
        cardsPressable: [...document.querySelectorAll('.poker-card')]
            .every(c => c.hasAttribute('aria-pressed'))
    })""")
    assert a11y["decorationHidden"]
    assert a11y["tallyAnnounced"] and a11y["seatsAnnounced"]
    assert a11y["everyStateIsText"]
    assert set(a11y["states"]) <= {"Tu voto", "Votó", "Pensando", "Ausente"}
    assert a11y["cardsLabelled"] and a11y["cardsPressable"]


def test_arrow_keys_walk_around_the_table(live_server, page, table):
    table["seat"](4)
    enter_room(live_server, page, table)

    page.eval_on_selector(".seat-avatar[data-throw-target]", "el => el.focus()")
    first = page.evaluate("() => document.activeElement.getAttribute('aria-label')")
    page.keyboard.press("ArrowRight")
    second = page.evaluate("() => document.activeElement.getAttribute('aria-label')")
    page.keyboard.press("ArrowLeft")
    back = page.evaluate("() => document.activeElement.getAttribute('aria-label')")

    assert first != second, "the arrow keys did not move between faces"
    assert back == first


def test_a_phone_never_scrolls_sideways(live_server, page, table):
    table["seat"](7, votes=["8", "5", None, "8", None, "13", "8"])
    enter_room(live_server, page, table, width=390, height=844)

    phone = page.evaluate(r"""() => ({
        pageLeaks: document.documentElement.scrollWidth > window.innerWidth + 1,
        /* Name the culprit, otherwise this failure is a riddle. An element only
           counts if nothing above it scrolls: a wide row inside a scroller is fine. */
        culprits: (() => {
            const vw = window.innerWidth, found = [];
            document.querySelectorAll('*').forEach(el => {
                if (el.getBoundingClientRect().right <= vw + 1) return;
                for (let up = el.parentElement; up && up !== document.body; up = up.parentElement) {
                    const ovx = getComputedStyle(up).overflowX;
                    if (ovx === 'auto' || ovx === 'scroll' || ovx === 'hidden') return;
                }
                found.push(el.tagName.toLowerCase() +
                    (el.id ? '#' + el.id : '') +
                    (typeof el.className === 'string' && el.className.trim()
                        ? '.' + el.className.trim().split(/\s+/)[0] : '') +
                    ' right=' + Math.round(el.getBoundingClientRect().right));
            });
            return found.slice(0, 6);
        })(),
        scrollWidth: document.documentElement.scrollWidth,
        viewport: window.innerWidth,
        ovalHidden: getComputedStyle(document.querySelector('.table-oval')).display === 'none',
        seatsAreAStrip:
            getComputedStyle(document.getElementById('participants-list')).position === 'static',
        stripScrolls:
            getComputedStyle(document.getElementById('participants-list')).overflowX === 'auto',
        everySeatReachable: document.querySelectorAll('.table-seat').length,
        tallyStillThere: document.getElementById('table-tally').textContent
    })""")
    assert not phone["pageLeaks"], (
        f"the page scrolls sideways on a phone: {phone['scrollWidth']}px of content in "
        f"{phone['viewport']}px. Widest offenders not inside a scroller: {phone['culprits']}"
    )
    assert phone["ovalHidden"] and phone["seatsAreAStrip"] and phone["stripScrolls"]
    assert phone["everySeatReachable"] == 8
    assert phone["tallyStillThere"] == "5 de 8 han votado"
