import cv2
# import keras
import shutil
import pathlib
import numpy as np
from sc2 import maps, BotAI, Difficulty, Race, run_game, position, Result
from sc2.ids.ability_id import AbilityId
from sc2.ids.buff_id import BuffId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.player import Bot, Computer
import random
import time
HEADLESS = False

class CompetetiveBot(BotAI):
    def __init__(self, use_model=False):
        super().__init__()
        self.do_something_after = 0
        # self.use_model = use_model
        self.train_data = []
        # if self.use_model:
        #     print("USING MODEL!")
        #     self.model = keras.models.load_model("BasicCNN-30-epochs-0.0001-LR-4.2")

    async def on_step(self, iteration):
        self.iteration = iteration
        await self.great(iteration)
        await self.chrono()
        await self.scout()
        await self.intel()
        await self.attack()
        await self.distribute_workers()
        await self.build_pylon()
        await self.build_workers()
        await self.expansion()
        await self.build_offensive_stuctures()
        await self.build_geyser()
        await self.train_units()      
    
    def on_end(self, game_result: Result):
        print('--- on_end called ---')
        print(game_result)
        if game_result == Result.Victory:
            start_dir = str(pathlib.Path().resolve())
            end_dir = str(pathlib.Path().resolve()) + "/traindata"
            file_name = "train_data{}.npy".format(str(int(time.time())))
            np.save(file_name, np.array(self.train_data, dtype=object))
            shutil.move(start_dir + "/" + file_name, end_dir + "/" + file_name)
  
        
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

    async def intel(self):
        game_data = np.zeros((self.game_info.map_size[1], self.game_info.map_size[0], 3), np.uint8)
        draw_dict = {
                     UnitTypeId.NEXUS: [15, (0, 255, 0)],
                     UnitTypeId.PYLON: [3, (20, 235, 0)],
                     UnitTypeId.PROBE: [1, (55, 200, 0)],
                     UnitTypeId.ASSIMILATOR: [2, (55, 200, 0)],
                     UnitTypeId.GATEWAY: [3, (200, 100, 0)],
                     UnitTypeId.CYBERNETICSCORE: [3, (150, 150, 0)],
                     UnitTypeId.STARGATE: [5, (255, 0, 0)],
                     UnitTypeId.ROBOTICSFACILITY: [5, (215, 155, 0)]
                    }
        
        for unit_type in draw_dict:
            for unit in self.structures(unit_type).ready:
                pos = unit.position
                cv2.circle(game_data, (int(pos[0]), int(pos[1])), draw_dict[unit_type][0], draw_dict[unit_type][1], -1)
        main_base_names = ["nexus", "commandcenter", "hatchery"]
        
        for enemy_building in self.enemy_structures:
            pos = enemy_building.position
            if enemy_building.name.lower() not in main_base_names:
                cv2.circle(game_data, (int(pos[0]), int(pos[1])), 5, (200, 50, 212), -1)
            else:
                cv2.circle(game_data, (int(pos[0]), int(pos[1])), 15, (0, 0, 255), -1)
        
        for enemy_unit in self.enemy_units:
            if not enemy_unit.is_structure:
                worker_names = ["probe",
                                "scv",
                                "drone"]
                pos = enemy_unit.position
                if enemy_unit.name.lower() in worker_names:
                    cv2.circle(game_data, (int(pos[0]), int(pos[1])), 1, (55, 0, 155), -1)
                else:
                    cv2.circle(game_data, (int(pos[0]), int(pos[1])), 3, (50, 0, 215), -1)
        
        for obs in self.units(UnitTypeId.OBSERVER).ready:
            pos = obs.position
            cv2.circle(game_data, (int(pos[0]), int(pos[1])), 1, (255, 255, 255), -1)

        for vr in self.units(UnitTypeId.VOIDRAY).ready:
            pos = vr.position
            cv2.circle(game_data, (int(pos[0]), int(pos[1])), 3, (255, 100, 0), -1)

        for st in self.units(UnitTypeId.STALKER).ready:
            pos = st.position
            cv2.circle(game_data, (int(pos[0]), int(pos[1])), 2, (255, 200, 0), -1)
        line_max = 50
        
        mineral_ratio = self.minerals / 1500
        if mineral_ratio > 1.0:
            mineral_ratio = 1.0
        
        vespene_ratio = self.vespene / 1500
        if vespene_ratio > 1.0:
            vespene_ratio = 1.0

        population_ratio = self.supply_left / self.supply_cap
        if population_ratio > 1.0:
            population_ratio = 1.0
        
        plausible_supply = self.supply_cap / 200.0
        military_weight = 0
        if self.supply_cap-self.supply_left !=0:
            military_weight = len(self.units(UnitTypeId.VOIDRAY)) / (self.supply_cap-self.supply_left)
        if military_weight > 1.0:
            military_weight = 1.0
        
        cv2.line(game_data, (0, 19), (int(line_max*military_weight), 19), (250, 250, 200), 3)
        cv2.line(game_data, (0, 15), (int(line_max*plausible_supply), 15), (220, 200, 200), 3)
        cv2.line(game_data, (0, 11), (int(line_max*population_ratio), 11), (150, 150, 150), 3)
        cv2.line(game_data, (0, 7), (int(line_max*vespene_ratio), 7), (210, 200, 0), 3)
        cv2.line(game_data, (0, 3), (int(line_max*mineral_ratio), 3), (0, 255, 25), 3)
        
        self.flipped = cv2.flip(game_data, 0)
        if not HEADLESS:
            resized = cv2.resize(self.flipped, dsize=None, fx=2, fy=2)
            cv2.imshow('Intel', resized)
            cv2.waitKey(1)

    async def scout(self):
        if self.units(UnitTypeId.OBSERVER).amount > 0:
            scout = self.units(UnitTypeId.OBSERVER)[0]
            if scout.is_idle:
                enemy_location = self.enemy_start_locations[0]
                move_to = self.random_location_variance(enemy_location)
                scout.move(move_to)
        else:
            for rf in self.structures(UnitTypeId.ROBOTICSFACILITY).ready.idle:
                if self.can_afford(UnitTypeId.OBSERVER) and self.supply_left > 0:
                    rf.train(UnitTypeId.OBSERVER)
    
    def random_location_variance(self, enemy_start_location):
        x = enemy_start_location[0]
        y = enemy_start_location[1]

        x += ((random.randrange(-100, 100))/10) * self.game_info.map_size[0]
        y += ((random.randrange(-100, 100))/10) * self.game_info.map_size[1]

        if x < 0:
            x = 0
        if y < 0:
            y = 0
        if x > self.game_info.map_size[0]:
            x = self.game_info.map_size[0]
        if y > self.game_info.map_size[1]:
            y = self.game_info.map_size[1]

        go_to = position.Point2(position.Pointlike((x,y)))

        return go_to

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
        aggressive_units = {UnitTypeId.STALKER: [7, 3],
                            UnitTypeId.VOIDRAY: [9, 3]}

        for UNIT in aggressive_units:
            if self.units(UNIT).idle.amount > aggressive_units[UNIT][0] and self.units(UNIT).idle.amount > aggressive_units[UNIT][1]:
                choice = random.randrange(0, 3)
                target = False
                if self.iteration > self.do_something_after:
                    for s in self.units(UNIT).idle:
                        if choice == 0:
                            tgt = self.enemy_units.filter(lambda unit: unit.can_be_attacked)
                            if tgt:
                                target = tgt.closest_to(random.choice(self.structures(UnitTypeId.NEXUS)))
                        elif choice == 1:
                            tgt = self.enemy_structures.filter(lambda unit: unit.can_be_attacked)
                            if tgt:
                                target = tgt.closest_to(s)
                        elif choice == 2:
                            target = self.enemy_start_locations[0]
                        if target:
                                s.attack(target)
                        y = np.zeros(3)
                        y[choice] = 1
                        self.train_data.append([y, self.flipped])
            elif self.units(UNIT).idle.amount > aggressive_units[UNIT][1]:
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
                    if self.can_afford(UnitTypeId.CYBERNETICSCORE) and not self.already_pending(UnitTypeId.CYBERNETICSCORE):
                        await self.build(UnitTypeId.CYBERNETICSCORE, near=pylon)
            
            elif self.structures(UnitTypeId.GATEWAY).amount < 1:
                if self.can_afford(UnitTypeId.GATEWAY) and not self.already_pending(UnitTypeId.GATEWAY):
                    await self.build(UnitTypeId.GATEWAY, near=pylon)
            
            if self.structures(UnitTypeId.CYBERNETICSCORE).ready:
                if self.structures(UnitTypeId.ROBOTICSFACILITY).amount < 1:
                    if self.can_afford(UnitTypeId.ROBOTICSFACILITY) and not self.already_pending(UnitTypeId.ROBOTICSFACILITY):
                        await self.build(UnitTypeId.ROBOTICSFACILITY, near=pylon) 
            
            if self.structures(UnitTypeId.CYBERNETICSCORE).ready:
                if self.structures(UnitTypeId.STARGATE).ready.amount < 3:
                    if self.can_afford(UnitTypeId.STARGATE) and not self.already_pending(UnitTypeId.STARGATE):
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

for i in range(1):
    map = random.choice(maps.get())
    print(map)
    run_game(
        map,
        [Bot(Race.Protoss, CompetetiveBot()),
        Computer(Race.Random, Difficulty.VeryHard)],
        realtime=False
    )
