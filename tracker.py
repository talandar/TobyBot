class BattleData(object):

    combatants = {}
    combat_active = False

    def __init__(self):
        print("init battledata")

    def __str__(self):
        out = f"{'Active' if self.combat_active else 'Inactive'} combat with {len(self.combatants)} combatants."
        for combatant in self.combatants.values():
            out = out + '\n' + str(combatant)
        return out

    def add_combatant(self, combatant):
        self.combatants[combatant.name] = combatant

    def remove_combatant(self, name):
        removed = self.combatants.pop(name, None)
        return removed

    def get_combatant(self, name):
        self.combatants.get(name, None)

    def get_names_with_prefix(self, prefix):
        matches = []
        for combatant_name in self.combatants.keys():
            if combatant_name.startswith(prefix):
                matches.append(combatant_name)
        return matches

    def set_initiative(self, name, score):
        if name in self.combatants:
            self.combatants[name].initiative = score
            return self.combatants[name]
        else:
            return None


class BattleCombatant(object):

    def __init__(self, name, maxhp, curhp=None, flags=None):
        self.name = name
        self.maxhp = maxhp
        self.temphp = 0
        self.initiative = -1
        self.has_had_turn = False
        self.status = ''
        if curhp:
            self.curhp = curhp
        else:
            self.curhp = self.maxhp
        if flags:
            self.flags = flags
        else:
            self.flags = CombatantFlags()

    def __str__(self):
        return f"[{self.name}: {self.curhp}/{self.maxhp}{f', {self.temphp} temp' if self.temphp > 0 else ''}.  Initiative {self.initiative}, Status: '{self.status}'.  Flags: {self.flags}]"

    def damage(self, damage, data):
        damage_after_tmphp = damage - self.temphp
        if damage_after_tmphp > 0:
            self.temphp = 0
            self.curhp = self.curhp - damage_after_tmphp
            if self.curhp <= 0:
                self.curhp = 0
                # TODO set up dying status?
                if self.flags.remove_on_death:
                    data.pop(self.name, None)
        else:
            self.temphp = self.temphp - damage


class CombatantFlags(object):

    def __init__(self, hide_hp=False, hide_name=False, remove_on_death=False):
        self.hide_hp = hide_hp
        self.hide_name = hide_name
        self.remove_on_death = remove_on_death

    def set_flag(self, name):
        if name == "hidehp":
            self.hide_hp = True
        elif name == "hidename":
            self.hide_name = True
        elif name == "removeondeath":
            self.remove_on_death = True
        else:
            print(f"unknown flag: {name}")

    def __str__(self):
        flags = []
        if self.hide_hp:
            flags.append("Hide HP")
        if self.hide_name:
            flags.append("Hide Name")
        if self.remove_on_death:
            flags.append("Remove on Death")
        return "[" + ", ".join(flags) + "]"


def main():
    c = BattleCombatant('foo', 10, flags=CombatantFlags(False, False, True))
    c.temphp = 5
    c.damage(5, None)
    print(c)


if __name__ == "__main__":
    main()
