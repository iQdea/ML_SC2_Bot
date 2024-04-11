from tabnanny import check
from Hard.constants import *
from sc2 import maps, BotAI, Difficulty, Race, run_game
from sc2.ids.ability_id import AbilityId
from sc2.ids.buff_id import BuffId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.player import Bot, Computer

class CompetitiveBot(BotAI):
    def __init__(self):
        self.proxy_built = False
        self.onegate = False

    async def on_step(self, iteration):
        # Populate this function with whatever your bot should do!
        await self.distribute_workers()
        await self.chrono()
        await self.build_workers()
        await self.build_pylon()
        await self.build_gas()
        await self.build_gateway()
        await self.build_cybercore()
        await self.train_stalkers()
        await self.warpgate_research()
        await self.warp()
        await self.attack()
        pass

    async def check_nexus(self):
        if not self.townhalls.ready:
            for worker in self.workers:
                worker.attack(self.enemy_start_locations[0])
            return 0
        else:
            return self.townhalls.ready.random

    async def build_workers(self):
        nexus = await self.check_nexus()
        if nexus == 0:
            return
        else:
            if self.can_afford(PROBE) and nexus.is_idle and self.workers.amount < self.townhalls.amount * 22 and self.minerals > 0:
                nexus.train(PROBE)

    async def build_pylon(self):
        nexus = await self.check_nexus()
        if nexus == 0:
            return
        else:
            pos = nexus.position.towards(self.enemy_start_locations[0], 10)
            if self.supply_left < 3 and self.already_pending(PYLON) == 0 and self.can_afford(PYLON):
                await self.build(PYLON, near=pos)
            if self.structures(GATEWAY).amount == 4 and not self.proxy_built and self.can_afford(PYLON):
                pos = self.game_info.map_center.towards(self.enemy_start_locations[0], 10)
                await self.build(PYLON, near = pos)
                self.proxy_built = True

    async def build_gateway(self):
        if self.structures(PYLON).ready and self.can_afford(GATEWAY):
            if not self.structures(GATEWAY).amount == 4 and not self.structures(FGATEWAY).amount == 4:
                if not self.onegate:
                    pylon = self.structures(PYLON).ready.first
                    await self.build(GATEWAY, near = pylon)
                    self.onegate = True
                else:
                    pylon = self.structures(PYLON).ready.closer_than(50, self.structures(PYLON).ready.first).random
                    await self.build(GATEWAY, near = pylon)
                

    async def build_gas(self):
        for nexus in self.townhalls.ready:
            vgs = self.vespene_geyser.closer_than(15, nexus)
            for vg in vgs:
                if not self.can_afford(ASSIMILATOR):
                    break
                worker = self.select_build_worker(vg.position)
                if worker is None:
                    break
                if not self.gas_buildings or not self.gas_buildings.closer_than(1, vg):
                    worker.build(ASSIMILATOR, vg)
                    worker.stop(queue=True)
    
    async def build_cybercore(self):
        if self.structures(PYLON).ready:
            pylon = self.structures(PYLON).ready.closer_than(50, self.structures(PYLON).ready.first).random
            if self.structures(GATEWAY).ready:
                if not self.structures(CYBERNETICSCORE):
                    if self.can_afford(CYBERNETICSCORE) and self.already_pending(CYBERNETICSCORE) == 0:
                        await self.build(CYBERNETICSCORE, near=pylon)
    
    async def train_stalkers(self):
        for gateway in self.structures(GATEWAY).ready:
            if self.can_afford(STALKER) and gateway.is_idle:
                gateway.train(STALKER)

    async def chrono(self):
        nexus = await self.check_nexus()
        if nexus == 0:
            return
        else:
            if not nexus.is_idle and not nexus.has_buff(BuffId.CHRONOBOOSTENERGYCOST):
                nexuses = self.structures(UnitTypeId.NEXUS)
                abilities = await self.get_available_abilities(nexuses)
                for nexus, abilities_nexus in zip(nexuses, abilities):
                    if AbilityId.EFFECT_CHRONOBOOSTENERGYCOST in abilities_nexus:
                        if not self.structures(CYBERNETICSCORE).ready:
                            nexus(AbilityId.EFFECT_CHRONOBOOSTENERGYCOST, nexus)
                            break
                        elif self.structures(CYBERNETICSCORE).ready \
                            and self.already_pending_upgrade(WR) > 0 and self.already_pending_upgrade(WR) < 1:
                            cybercore = self.structures(CYBERNETICSCORE).ready.random
                            nexus(AbilityId.EFFECT_CHRONOBOOSTENERGYCOST, cybercore)
                            break
                        else:
                            nexus(AbilityId.EFFECT_CHRONOBOOSTENERGYCOST, nexus)
                            break

    async def warpgate_research(self):
        if self.structures(CYBERNETICSCORE).ready and self.can_afford(RW) and self.already_pending_upgrade(WR) == 0:
            cybercore = self.structures(CYBERNETICSCORE).ready.first
            cybercore.research(WR)
    
    async def attack(self):
        stalk_cnt = self.units(STALKER).amount
        stalkrs = self.units(STALKER).ready.idle
        
        for st in stalkrs:
            if stalk_cnt > 10:
                targets = (self.enemy_units | self.enemy_structures).filter(lambda unit: unit.can_be_attacked)
                if targets:
                    target = targets.closest_to(st)
                    st.attack(target)
                else:
                    st.attack(self.enemy_start_locations[0])

    async def expand(self):
        if self.townhalls.amount < 2 and self.can_afford(UnitTypeId.NEXUS):
            await self.expand_now()

    async def warp(self):
        for wp in self.structures(FGATEWAY).ready:
            abilities = await self.get_available_abilities(wp)
            proxy = self.structures(PYLON).closest_to(self.enemy_start_locations[0])
            if AbilityId.WARPGATETRAIN_STALKER in abilities and self.can_afford(STALKER):
                placement = await self.find_placement(AbilityId.WARPGATETRAIN_STALKER, proxy.position.random_on_distance(4), placement_step=1)
                if placement is None:
                    print("can't place")
                    return
                wp.warp_in(STALKER, placement)

def main():
    run_game(
        maps.get("AbyssalReefLE"),
        [Bot(Race.Protoss, CompetitiveBot()),
         Computer(Race.Terran, Difficulty.Hard)],
        realtime=False,
    )


if __name__ == "__main__":
    main()