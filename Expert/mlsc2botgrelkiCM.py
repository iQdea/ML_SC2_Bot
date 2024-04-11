from sc2 import maps, BotAI, Difficulty, Race, run_game
from sc2.ids.ability_id import AbilityId
from sc2.ids.buff_id import BuffId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.player import Bot, Computer
class CompetetiveBot(BotAI):
    def __init__(self):
        super().__init__()
        # self.ITERATIONS_PER_MINUTE = 165

    async def on_step(self, iteration):
        self.iteration = iteration
        await self.great(iteration)
        await self.chrono()
        await self.attack()
        await self.distribute_workers()
        await self.build_pylon()
        await self.build_workers()
        await self.expansion()
        await self.build_offensive_stuctures()
        await self.build_geyser()
        await self.train_units()
        
    async def great(self, iteration):
        if iteration == 0:
            await self.chat_send("(glhf)")
    
    async def check_nexus(self):
        if not self.townhalls.ready:
            for worker in self.workers:
                worker.attack(self.enemy_start_locations[0])
            return 0
        else:
            return self.townhalls.ready.random

    async def chrono(self):
        nexus = await self.check_nexus()
        if nexus != 0:
            if not nexus.is_idle and not nexus.has_buff(BuffId.CHRONOBOOSTENERGYCOST):
                nexuses = self.structures(UnitTypeId.NEXUS)
                abilities = await self.get_available_abilities(nexuses)
                for loop_nexus, abilities_nexus in zip(nexuses, abilities):
                    if AbilityId.EFFECT_CHRONOBOOSTENERGYCOST in abilities_nexus:
                        loop_nexus(AbilityId.EFFECT_CHRONOBOOSTENERGYCOST, nexus)
                        break
    def find_target(self, state):
        targets = (self.enemy_units | self.enemy_structures).filter(lambda unit: unit.can_be_attacked)
        if targets:
            return targets.closest_to(state)
        else:
            return self.enemy_start_locations[0]

    async def attack(self):

        aggressive_units = {UnitTypeId.STALKER: [9, 3],
                            UnitTypeId.VOIDRAY: [6, 3]}
        summary = []
        for value in (zip(*list(aggressive_units.values()))):
           summary.append(sum(value))
        summary = summary[0]

        for UNIT in aggressive_units:
            if self.units(UNIT).amount > aggressive_units[UNIT][0] and self.units(UNIT).amount > aggressive_units[UNIT][1] and self.army_count >= summary:
                for s in self.units(UNIT).idle:
                    if s.weapon_cooldown > 0 and UNIT == UnitTypeId.VOIDRAY:
                        s(AbilityId.EFFECT_VOIDRAYPRISMATICALIGNMENT)    
                    s.attack(self.find_target(s))
            elif self.units(UNIT).amount > aggressive_units[UNIT][1]:
                for s in self.units(UNIT).idle:
                        s.attack(self.townhalls.closest_to(self.enemy_start_locations[0]).position)
    
    async def build_pylon(self):
        nexus = await self.check_nexus()
        if nexus != 0:
            if (
                self.supply_left < 2 and self.already_pending(UnitTypeId.PYLON) == 0
                or self.supply_used > 15 and self.supply_left < 4 and self.already_pending(UnitTypeId.PYLON) < 2
            ):
                if self.can_afford(UnitTypeId.PYLON):
                    await self.build(UnitTypeId.PYLON, near=nexus)

    async def build_workers(self):
        nexus = await self.check_nexus()
        if nexus != 0:
            if self.supply_workers + self.already_pending(UnitTypeId.PROBE) < self.townhalls.amount * 22 and nexus.is_idle:
                if self.can_afford(UnitTypeId.PROBE):
                    nexus.train(UnitTypeId.PROBE)
    
    async def expansion(self):
        if self.townhalls.ready.amount + self.already_pending(UnitTypeId.NEXUS) < 3:
            if self.can_afford(UnitTypeId.NEXUS):
                await self.expand_now()

    async def build_offensive_stuctures(self):
        if self.structures(UnitTypeId.PYLON).ready:
            pylon = self.structures(UnitTypeId.PYLON).ready.random
            if self.structures(UnitTypeId.GATEWAY).ready and not self.structures(UnitTypeId.CYBERNETICSCORE):
                    if (
                        self.can_afford(UnitTypeId.CYBERNETICSCORE)
                        and not self.already_pending(UnitTypeId.CYBERNETICSCORE)
                    ):
                        await self.build(UnitTypeId.CYBERNETICSCORE, near=pylon)
            elif self.structures(UnitTypeId.GATEWAY).amount < 3:
                if self.can_afford(UnitTypeId.GATEWAY) and not self.already_pending(UnitTypeId.GATEWAY):
                    await self.build(UnitTypeId.GATEWAY, near=pylon)
            elif self.structures(UnitTypeId.GATEWAY).amount == 3:
                if (
                self.townhalls.ready.amount + self.already_pending(UnitTypeId.NEXUS) >= 3
                and self.structures(UnitTypeId.STARGATE).ready.amount + self.already_pending(UnitTypeId.STARGATE) < 3
                ):
                    if self.can_afford(UnitTypeId.STARGATE):
                        await self.build(UnitTypeId.STARGATE, near=pylon)

    async def build_geyser(self):
        if self.structures(UnitTypeId.CYBERNETICSCORE):
            for nexus in self.townhalls.ready:
                vgs = self.vespene_geyser.closer_than(15, nexus)
                for vg in vgs:
                    if not self.can_afford(UnitTypeId.ASSIMILATOR):
                        break

                    worker = self.select_build_worker(vg.position)
                    if worker is None:
                        break

                    if not self.gas_buildings or not self.gas_buildings.closer_than(1, vg):
                        worker.build(UnitTypeId.ASSIMILATOR, vg)
                        worker.stop(queue=True)

    async def train_units(self):
        for gw in self.structures(UnitTypeId.GATEWAY).ready.idle:
            if self.units(UnitTypeId.STALKER).amount < self.units(UnitTypeId.VOIDRAY).amount:
                if self.can_afford(UnitTypeId.STALKER) and self.supply_left > 0:
                    gw.train(UnitTypeId.STALKER)

        if self.townhalls.amount >= 3:
            for sg in self.structures(UnitTypeId.STARGATE).ready.idle:
                if self.can_afford(UnitTypeId.VOIDRAY) and self.supply_left > 0:
                    sg.train(UnitTypeId.VOIDRAY)

# from sc2.data import AIBuild
# from s2clientprotocol.sc2api_pb2 import AIBuild as Ab


def main():
    # print(Ab.items())
    run_game(
        maps.get("AbyssalReefLE"),
        [Bot(Race.Protoss, CompetetiveBot()),
        Computer(Race.Terran, Difficulty.Hard)],
        realtime=False
    )


if __name__ == "__main__":
    main()