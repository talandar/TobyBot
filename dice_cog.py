
import re
import d20
import nextcord
from nextcord.ext import commands
from utils import BladesStringifier, VerboseMDStringifier, PersistentRollContext, safe_send, get_register_guilds


ADV_WORD_RE = re.compile(r"(?:^|\s+)(adv|dis)(?:\s+|$)")


def string_search_adv(dice_str: str):
    """
    Given a dice string, returns whether the word adv or dis was found within it, and the string with the word removed.
    >>> string_search_adv("1d20 adv")
    ("1d20 ", d20.AdvType.ADV)
    >>> string_search_adv("1d20")
    ("1d20", d20.AdvType.NONE)
    """
    adv = d20.AdvType.NONE
    if (match := ADV_WORD_RE.search(dice_str)) is not None:
        adv = d20.AdvType.ADV if match.group(1) == "adv" else d20.AdvType.DIS
        return dice_str[: match.start(1)] + dice_str[match.end():], adv
    return dice_str, adv


class Dice(commands.Cog):
    """Dice and math related commands."""

    def __init__(self, bot):
        self.bot = bot

# This is straight up stolen from avrae!
    @nextcord.slash_command(guild_ids=get_register_guilds())
    async def roll(self, interaction: nextcord.Interaction, *, dice: str = "1d20"):
        """Roll is used to roll any combination of dice in the `XdY` format. (`1d6`, `2d8`, etc)
        Multiple rolls can be added together as an equation. Standard Math operators and Parentheses can be used: `() + - / *`
        Roll also accepts `adv` and `dis` for Advantage and Disadvantage. Rolls can also be tagged with `[text]` for informational purposes. Any text after the roll will assign the name of the roll.
        ___Examples___
        `!r` or `!r 1d20` - Roll a single d20, just like at the table
        `!r 1d20+4` - A skill check or attack roll
        `!r 1d8+2+1d6` - Longbow damage with Hunter’s Mark
        `!r 1d20+1 adv` - A skill check or attack roll with Advantage
        `!r 1d20-3 dis` - A skill check or attack roll with Disadvantage
        `!r (1d8+4)*2` - Warhammer damage against bludgeoning vulnerability
        **Advanced Options**
        __Operators__
        Operators are always followed by a selector, and operate on the items in the set that match the selector.
        A set can be made of a single or multiple entries i.e. `1d20` or `(1d6,1d8,1d10)`
        These operations work on dice and sets of numbers
        `k` - keep - Keeps all matched values.
        `p` - drop - Drops all matched values.
        These operators only work on dice rolls.
        `rr` - reroll - Rerolls all matched die values until none match.
        `ro` - reroll - once - Rerolls all matched die values once.
        `ra` - reroll and add - Rerolls up to one matched die value once, add to the roll.
        `mi` - minimum - Sets the minimum value of each die.
        `ma` - maximum - Sets the maximum value of each die.
        `e` - explode on - Rolls an additional die for each matched die value. Exploded dice can explode.
        __Selectors__
        Selectors select from the remaining kept values in a set.
        `X`  | literal X
        `lX` | lowest X
        `hX` | highest X
        `>X` | greater than X
        `<X` | less than X
        __Examples__
        `!r 2d20kh1+4` - Advantage roll, using Keep Highest format
        `!r 2d20kl1-2` - Disadvantage roll, using Keep Lowest format
        `!r 4d6mi2` - Elemental Adept, minimum 2 on each dice
        `!r 10d6ra6` - Wild Magic Sorcerer Spell Bombardment
        `!r 4d6ro<3` - Great Weapon Fighting
        `!r 2d6e6` - Explode on 6
        `!r (1d6,1d8,1d10)kh2` - Keep 2 highest rolls of a set of dice
        **Additional Information can be found at:**
        https://d20.readthedocs.io/en/latest/start.html#dice-syntax"""  # noqa: E501

        dice, adv = string_search_adv(dice)

        res = d20.roll(dice, advantage=adv, allow_comments=True, stringifier=VerboseMDStringifier())
        out = f"{interaction.user.mention}  :game_die:\n{str(res)}"
        if len(out) > 1999:
            out = f"{interaction.user.mention}  :game_die:\n{str(res)[:100]}...\n**Total**: {res.total}"

        await safe_send(interaction, out, allowed_mentions=nextcord.AllowedMentions(users=[interaction.user]))

    @nextcord.slash_command(guild_ids=get_register_guilds())
    async def multiroll(self, interaction: nextcord.Interaction, iterations: int, *, dice):
        """Rolls dice in xdy format a given number of times.
        Usage: multiroll <iterations> <dice>"""
        dice, adv = string_search_adv(dice)
        await self._roll_many(interaction, iterations, dice, adv=adv)

    @nextcord.slash_command(guild_ids=get_register_guilds())
    async def iterroll(self, interaction: nextcord.Interaction, iterations: int, dice, dc: int = None, *, args=""):
        """Rolls dice in xdy format, given a set dc.
        Usage: iterroll <iterations> <xdy> <DC> [args]"""
        _, adv = string_search_adv(args)
        await self._roll_many(interaction, iterations, dice, dc, adv)

    @nextcord.slash_command(guild_ids=get_register_guilds())
    async def bladesroll(self, interaction: nextcord.Interaction, numdice: int):
        """Rolls dice for blades in the dark.  Rolls a number of dice,
        as input.  Returning the highest value.  If two 6s are rolled,
        returns critical.  If zero is entered for number of dice, rolls
        two and returns the lowest."""
        if numdice > 0:
            rollexpr = f"{numdice}d6kh1"
        elif numdice == 0:
            rollexpr = "2d6ph1"
        else:
            await safe_send(interaction, "You can't roll a negative number of dice!")
            return
        res = d20.roll(rollexpr, stringifier=BladesStringifier())
        out = f"{interaction.user.mention}  :crossed_swords::game_die:\n{str(res)}"
        if len(out) > 1999:
            out = f"{interaction.user.mention}  :game_die:\n{str(res)[:100]}...\n**Total**: {res.total}"
        await safe_send(interaction, out, allowed_mentions=nextcord.AllowedMentions(users=[interaction.user]))

    @staticmethod
    async def _roll_many(interaction: nextcord.Interaction, iterations, roll_str, dc=None, adv=None):
        if iterations < 1 or iterations > 100:
            return await safe_send(interaction, "Too many or too few iterations.")
        if adv is None:
            adv = d20.AdvType.NONE
        results = []
        successes = 0
        ast = d20.parse(roll_str, allow_comments=True)
        roller = d20.Roller(context=PersistentRollContext())

        for _ in range(iterations):
            res = roller.roll(ast, advantage=adv)
            if dc is not None and res.total >= dc:
                successes += 1
            results.append(res)

        if dc is None:
            header = f"Rolling {iterations} iterations..."
            footer = f"{sum(o.total for o in results)} total."
        else:
            header = f"Rolling {iterations} iterations, DC {dc}..."
            footer = f"{successes} successes, {sum(o.total for o in results)} total."

        if ast.comment:
            header = f"{ast.comment}: {header}"

        result_strs = "\n".join(str(o) for o in results)

        out = f"{header}\n{result_strs}\n{footer}"

        if len(out) > 1500:
            one_result = str(results[0])
            out = f"{header}\n{one_result}\n[{len(results) - 1} results omitted for output size.]\n{footer}"

        await safe_send(interaction, f"{interaction.user.mention}\n{out}", allowed_mentions=nextcord.AllowedMentions(users=[interaction.user]))
