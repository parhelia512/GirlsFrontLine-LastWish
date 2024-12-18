import random
from .abstract import *


# 回合制游戏战斗系统
class TurnBasedBattleSystem(AbstractBattleSystemWithInGameDialog):
    def __init__(self) -> None:
        super().__init__()
        # 对话id查询用的字典
        self.__dialog_dictionary: dict = {}
        # 被选中的角色
        self.characterGetClick: Optional[str] = None
        self.enemiesGetAttack: dict = {}
        self.__action_choice: Optional[str] = None
        # 被选中的装饰物
        self.__decorationGetClick: int = -1
        # 缩进
        self.__zoomIn: int = 100
        self.__zoomIntoBe: int = 100
        # 是否在战斗状态-战斗loop
        self.__is_battle_mode: bool = False
        # 是否在等待
        self.__is_waiting: bool = True
        # 是否是死亡的那个
        self.the_dead_one: dict = {}
        # 谁的回合
        self.__whose_round: WhoseRound = WhoseRound.sangvisFerrisToPlayer
        # 技能对象
        self.__skill_target: tuple[str, ...] = tuple()
        # 被救助的那个角色
        self.friendGetHelp: Optional[str] = None
        # AI系统正在操控的敌对角色ID
        self.enemies_in_control_id: int = 0
        # 所有敌对角色的名字列表
        self.sangvisFerris_name_list: list = []
        # 战斗状态数据
        self.__statistics: BattleStatistics = BattleStatistics()
        # 储存角色受到伤害的文字surface
        self.__damage_do_to_characters: dict = {}
        self.__txt_alpha: Optional[int] = None
        # 移动路径
        self.the_route: list = []
        # 上个回合因为暴露被敌人发现的角色
        # 格式：角色：[x,y]
        self.the_characters_detected_last_round: dict = {}
        # 敌人的指令
        self.enemy_instructions: Optional[deque] = None
        # 敌人当前需要执行的指令
        self.current_instruction: Optional[HostileCharacter.DecisionHolder] = None
        # 积分栏的UI模块
        self.__RoundSwitchUI: Optional[RoundSwitch] = None
        # 可以互动的物品列表
        self.__thingsCanReact: list[linpg.DecorationObject] = []
        # 需要救助的角色列表
        self.friendsCanSave: list = []
        # 胜利目标
        self.__mission_objectives: dict = {}
        # 结束回合的图片
        self.__end_round_button: linpg.StaticImage = linpg.StaticImage.new_place_holder()
        # 当前回合的字体
        self.__current_round_txt: linpg.StaticImage = linpg.StaticImage.new_place_holder()
        # 关卡背景信息
        self.__battle_info: tuple[linpg.ImageSurface, ...] = tuple()
        # 加载用于渲染电影效果的上下黑色帘幕
        black_curtain: linpg.ImageSurface = linpg.surfaces.colored(
            (linpg.display.get_width(), linpg.display.get_height() // 7),
            linpg.colors.BLACK,
        )
        self.__up_black_curtain: linpg.MovableStaticImage = linpg.MovableStaticImage(
            black_curtain,
            0,
            -black_curtain.get_height(),
            0,
            0,
            0,
            black_curtain.get_height() * 5 // 100,
        )
        self.__down_black_curtain: linpg.MovableStaticImage = linpg.MovableStaticImage(
            black_curtain,
            0,
            linpg.display.get_height(),
            0,
            linpg.display.get_height() - black_curtain.get_height(),
            0,
            black_curtain.get_height() * 51 // 1000,
        )
        self.__frame_based_detection: set[str] = set()
        # 天气系统
        self.__weather_system: WeatherSystem = WeatherSystem()

    """关键重写或实现"""

    # 更新当前回合提示文字
    def __update_current_round_text(self) -> None:
        self.__current_round_txt = linpg.StaticImage(
            linpg.ArtisticFont.render_with_outline(
                linpg.lang.get_text("Battle_UI", "currentRound").format(
                    self.__statistics.total_rounds
                ),
                linpg.colors.WHITE,
                self._FONT.size,
            ),
            self.__end_round_button.left,
            self.__end_round_button.bottom,
        )
        self.__current_round_txt.set_width_with_original_image_size_locked(
            self.__end_round_button.width
        )
        self.__current_round_txt.set_right(self.__end_round_button.right)

    # 初始化ui
    def __init_ui(self) -> None:
        # 切换回合时的UI
        self.__RoundSwitchUI = RoundSwitch(
            linpg.display.get_width(), linpg.display.get_height()
        )
        # 加载结束回合的文字
        self.__end_round_txt = self._FONT.render(
            linpg.lang.get_text("Battle_UI", "endRound"), linpg.colors.WHITE
        )
        # 加载结束回合的按钮
        self.__end_round_button = linpg.load.static_image(
            r"Assets/image/UI/end_round_button.png",
            (0, linpg.display.get_height() * 4 // 5),
            (self.__end_round_txt.get_width() * 2, self.__end_round_txt.get_height() * 3),
        )
        self.__end_round_button.set_right(linpg.display.get_width() * 95 // 100)
        # 加载当前回合提示的文字
        self.__update_current_round_text()

    # 更新语言
    def update_language(self) -> None:
        super().update_language()
        self.selectMenuUI.update()
        # 初始化ui
        self.__init_ui()
        WarningMessageSystem.update_language()

    # 返回需要保存数据
    def _get_data_need_to_save(self) -> dict:
        return super()._get_data_need_to_save() | {
            "type": "battle",
            "statistics": self.__statistics.to_dict(),
        }

    # 停止
    def stop(self) -> None:
        super().stop()
        AttackingSoundManager.release()
        linpg.global_variables.remove("currentMode")

    # 加载进程
    def load_progress(self, _data: dict) -> None:
        if _data.get("type") == "battle":
            self._initialize(
                _data["chapter_type"], _data["chapter_id"], _data["project_name"]
            )
            DataToProcess: dict = linpg.config.load_file(self.get_data_file_path())
            DataToProcess.update(_data)
            if DataToProcess["type"] != "battle":
                raise Exception(
                    "Error: Cannot load the data from the progress file because the file type does not match"
                )
            # 加载地图与角色数据
            self.__start_loading(DataToProcess)
            # 初始化视觉小说系统
            self._update_dialog(
                DataToProcess.get("dialog_key", ""),
                DataToProcess.get("dialog_parameters", {}),
            )
            # 加载战斗状态数据
            self.__statistics.update(dict(DataToProcess["statistics"]))
        else:
            self.stop()
            # 设置参数
            linpg.global_variables.set("currentMode", value="dialog")
            linpg.global_variables.remove("chapterType")
            linpg.global_variables.set("chapterId", value=0)
            linpg.global_variables.remove("projectName")
            linpg.global_variables.remove("section")
            linpg.global_variables.set("saveData", value=_data)

    # 角色动画
    def _display_entities(self, screen: linpg.ImageSurface) -> None:
        if not self.__is_battle_mode:
            super()._display_entities(screen)
        else:
            # 画出用彩色方块表示的范围
            RangeSystem.draw(self.get_map(), screen)
            # 画出角色
            rightClickCharacterAlphaDeduct = True
            for faction in self._entities_data:
                for key, value in self._entities_data[faction].items():
                    assert isinstance(value, BasicEntity)
                    # 如果天亮的双方都可以看见/天黑，但是是友方角色/天黑，但是是敌方角色在可观测的范围内 -- 则画出角色
                    if value.attitude > 0 or self.get_map().is_coordinate_in_lit_area(
                        value.x, value.y
                    ):
                        if (
                            RangeSystem.get_visible()
                            and linpg.controller.mouse.get_pressed(2)
                        ):
                            if (
                                self._tile_is_hovering is not None
                                and self._tile_is_hovering[0] == int(value.x)
                                and self._tile_is_hovering[1] == int(value.y)
                            ):
                                rightClickCharacterAlphaDeduct = False
                                RangeSystem.set_target_alpha(255)
                                RangeSystem.update_attack_range(
                                    value.get_effective_range_coordinates(self.get_map())
                                )
                        value.render(screen, self.get_map())
                    else:
                        value.render(screen, self.get_map(), alpha=0)
                    # 是否有在播放死亡角色的动画（而不是倒地状态）
                    if (
                        not value.is_alive()
                        and key not in self.the_dead_one
                        and (value.kind == "HOC" or value.attitude < 0)
                    ):
                        self.the_dead_one[key] = value.attitude
                    # 伤害/治理数值显示
                    if key in self.__damage_do_to_characters:
                        the_alpha_to_check = self.__damage_do_to_characters[
                            key
                        ].get_alpha()
                        if the_alpha_to_check > 0:
                            xTemp, yTemp = self.get_map().calculate_position(
                                value.x, value.y
                            )
                            xTemp += self.get_map().tile_width // 20
                            yTemp -= self.get_map().tile_width // 20
                            display_in_center(
                                self.__damage_do_to_characters[key],
                                RangeSystem.get_image(0),
                                xTemp,
                                yTemp,
                                screen,
                            )
                            self.__damage_do_to_characters[key].set_alpha(
                                the_alpha_to_check - 5
                            )
                        else:
                            del self.__damage_do_to_characters[key]
            # 调整范围方块的透明度
            if not RangeSystem.get_visible() and self.characterGetClick is not None:
                RangeSystem.set_alpha(255)
            elif rightClickCharacterAlphaDeduct is True:
                RangeSystem.set_target_alpha(0)
            # 移除死亡的角色
            if len(self.the_dead_one) > 0:
                for key in tuple(self.the_dead_one.keys()):
                    if self.the_dead_one[key] < 0:
                        if (
                            self.enemies[key].get_imgId("die")
                            >= self.enemies[key].get_imgNum("die") - 1
                        ):
                            the_alpha = self.enemies[key].get_imgAlpha("die")
                            if the_alpha > 0:
                                self.enemies[key].set_imgAlpha(
                                    "die", the_alpha - linpg.display.get_delta_time()
                                )
                            else:
                                del self.the_dead_one[key]
                                del self.enemies[key]
                                self.__statistics.total_kills += 1
                    elif self.the_dead_one[key] > 0:
                        if (
                            self.alliances[key].get_imgId("die")
                            >= self.alliances[key].get_imgNum("die") - 1
                        ):
                            the_alpha = self.alliances[key].get_imgAlpha("die")
                            if the_alpha > 0:
                                self.alliances[key].set_imgAlpha(
                                    "die", the_alpha - linpg.display.get_delta_time()
                                )
                            else:
                                del self.the_dead_one[key]
                                del self.alliances[key]
                                self.__statistics.times_characters_down += 1

    def __check_entity_env_interaction(self, entityName: str) -> None:
        entity_value: FriendlyCharacter = self.alliances[entityName]
        # 检测是不是站在补给上
        _decorationOnPos = self.get_map().get_decoration(entity_value.get_pos())
        if (
            isinstance(_decorationOnPos, ChestObject)
            and entityName in _decorationOnPos.whitelist
        ):
            # 将物品按照类型放入列表
            for itemType, itemData in _decorationOnPos.items.items():
                if itemType == "bullet":
                    entity_value.add_bullets_carried(itemData)
                    self.__damage_do_to_characters[entityName] = self._FONT.render(
                        f"+ {itemData} {itemData, linpg.lang.get_texts('Battle_UI', 'bullets')}",
                        linpg.colors.ORANGE,
                    )
                elif itemType == "hp":
                    entity_value.heal(itemData)
                    self.__damage_do_to_characters[entityName] = self._FONT.render(
                        f"+ {itemData} hp", linpg.colors.GREEN
                    )
            # 移除箱子
            self.get_map().remove_decoration(_decorationOnPos)
        # 检测当前所在点是否应该触发对话
        name_from_by_pos: str = f"{entity_value.x}-{entity_value.y}"
        dialog_to_check: dict | None = self.__dialog_dictionary.get("move", {}).get(
            name_from_by_pos
        )
        if dialog_to_check is not None and entityName in dialog_to_check.get(
            "whitelist", (entityName,)
        ):
            self._update_dialog(str(dialog_to_check["dialog_key"]))
            self.__is_battle_mode = False
            # 如果对话不重复，则删除（默认不重复）
            if "repeat" not in dialog_to_check or not dialog_to_check["repeat"]:
                del self.__dialog_dictionary["move"][name_from_by_pos]

    def _display_map(self, screen: linpg.ImageSurface) -> None:
        super()._display_map(screen)
        # 检测角色所占据的装饰物（即需要透明化，方便玩家看到角色）
        charactersPos: list = []
        for value in self._entities_data.values():
            for dataDict in value.values():
                charactersPos.append((round(dataDict.x), round(dataDict.y)))
                charactersPos.append((round(dataDict.x) + 1, round(dataDict.y) + 1))
        # 展示场景装饰物
        self.get_map().display_decoration(screen, tuple(charactersPos))
        # 展示天气
        self.__weather_system.draw(screen, self.get_map().tile_size)
        # 展示所有角色Ui
        if self.__is_battle_mode is True or not self._is_any_dialog_playing():
            # 角色UI
            for _alliance in self.alliances.values():
                _alliance.drawUI(screen, self.get_map())
            for _enemy in self.enemies.values():
                if self.get_map().is_coordinate_in_lit_area(
                    round(_enemy.x), round(_enemy.y)
                ):
                    _enemy.drawUI(screen, self.get_map())

    # 修改父类的 _check_key_down 方法
    def _check_key_down(self, event: linpg.PG_Event) -> None:
        if self.__is_battle_mode is True:
            super()._check_key_down(event)

    def _check_key_up(self, event: linpg.PG_Event) -> None:
        if self.__is_battle_mode is True:
            super()._check_key_up(event)

    """加载与储存"""

    def new(
        self, chapterType: str, chapterId: int, projectName: Optional[str] = None
    ) -> None:
        self._initialize(chapterType, chapterId, projectName)
        # 加载地图与角色数据
        self.__start_loading(linpg.config.load_file(self.get_data_file_path()))
        # 初始化视觉小说系统
        self._update_dialog(self.__dialog_dictionary.get("initial", ""))
        # 初始化战斗状态数据
        self.__statistics = BattleStatistics()

    def _initialize(
        self, chapterType: str, chapterId: int, projectName: Optional[str]
    ) -> None:
        super()._initialize(chapterType, chapterId, projectName)
        ScoreBoard.need_updated()
        linpg.global_variables.set("currentMode", value="battle")
        linpg.global_variables.set("chapterType", value=self._chapter_type)
        linpg.global_variables.set("chapterId", value=self._chapter_id)
        linpg.global_variables.set("projectName", value=self._project_name)

    def __start_loading(self, _data: dict) -> None:
        # 初始化剧情模块
        self._init_dialog(dict(_data["dialogues"].get("data", {})))
        # 章节标题显示
        levelInfo: dict = self._get_level_info()
        LoadingTitle.update(
            linpg.lang.get_texts("Battle_UI", "numChapter"),
            self._chapter_id,
            levelInfo.get("title", linpg.lang.get_text("Global", "no_translation")),
            levelInfo.get("description", linpg.lang.get_text("Global", "no_translation")),
        )
        # 加载关卡背景介绍信息文字
        self.__battle_info = tuple(
            [
                self._FONT.render(_text, linpg.colors.WHITE)
                for _text in levelInfo.get(
                    "battle_info",
                    linpg.config.load(
                        r"Data/template/chapter_level_info_example.yaml",
                        linpg.setting.get_language(),
                        "battle_info",
                    ),
                )
            ]
        )
        # 初始化加载模块
        self._initialize_loading_module()
        # 渐入效果
        for i in range(1, 255, 2):
            LoadingTitle.draw(linpg.display.get_window(), i)
            linpg.display.flip()
        _task: threading.Thread = threading.Thread(
            target=self._process_data, args=(_data,)
        )
        _task.start()
        while _task.is_alive():
            LoadingTitle.draw(linpg.display.get_window())
            self._show_current_loading_progress(linpg.display.get_window())
            linpg.display.flip()
        # 加载完成，释放初始化模块占用的内存
        self._finish_loading()
        # 显示章节信息
        for i in range(0, 250, 2):
            LoadingTitle.draw(linpg.display.get_window())
            self.__draw_battle_info(linpg.display.get_window(), i)
            linpg.display.flip()
        # 重置RangeSystem状态
        RangeSystem.set_visible(True)

    # 加载游戏进程
    def _process_data(self, _data: dict) -> None:
        # 生成标准文字渲染器
        self._FONT.update(linpg.display.get_width() // 76)
        # 加载按钮的文字
        self.selectMenuUI = SelectMenu()
        WarningMessageSystem.init(linpg.display.get_height() // 33)
        # 设置背景音乐
        self.set_bgm(os.path.join("Assets", "music", _data["background_music"]))
        # 加载胜利目标
        self.__mission_objectives.clear()
        self.__mission_objectives.update(_data["mission_objectives"])
        # 初始化天气和环境的音效 -- 频道1
        self.environment_sound = linpg.SoundsManager(1)
        if _data["weather"] is not None:
            self.environment_sound.add(
                os.path.join(
                    "Assets", "sound", "environment", "{}.ogg".format(_data["weather"])
                )
            )
            self.__weather_system.init(_data["weather"])
        # 加载对话信息
        self.__dialog_dictionary.clear()
        self.__dialog_dictionary.update(_data["dialogues"].get("dictionary", {}))
        # 开始加载关卡
        super()._process_data(_data)
        # 重新计算光亮区域
        self._update_darkness()
        # 初始化ui
        self.__init_ui()
        # 加载子弹图片
        # bullet_img = load.img("Assets/image/UI/bullet.png", get_tile_width()/6, self.get_map().tile_height/12)
        RangeSystem.update_size(self.get_map().tile_size * 4 // 5)
        # 角色信息UI管理
        self.__characterInfoBoard = CharacterInfoBoard()
        """-----加载音效-----"""
        # 更新所有音效的音量
        self._update_sound_volume()
        # 攻击的音效 -- 频道2
        AttackingSoundManager.initialize()
        # 加载脚步声
        self._footstep_sounds.clear()
        for walkingSoundPath in glob(r"Assets/sound/snow/*.wav"):
            self._footstep_sounds.add(walkingSoundPath)

    """画面"""

    # 更新音量
    def _update_sound_volume(self) -> None:
        super()._update_sound_volume()
        self.environment_sound.set_volume(linpg.volume.get_environment() / 100.0)

    # 警告某个角色周围的敌人
    def __alert_enemy_around(self, name: str, value: int = 20) -> None:
        enemies_need_check: list = []
        for key in self.enemies:
            if self.enemies[key].range_target_in(self.alliances[name]) >= 0:
                self.enemies[key].alert(value)
                self.characterInControl.notice(value)
                enemies_need_check.append(key)
        for key in enemies_need_check:
            if self.enemies[key].is_alert:
                for character in self.alliances:
                    if self.enemies[key].range_target_in(self.alliances[character]) >= 0:
                        self.alliances[character].notice(100)

    # 显示关卡信息
    def __draw_battle_info(self, screen: linpg.ImageSurface, _alpha: int) -> None:
        for i in range(len(self.__battle_info)):
            self.__battle_info[i].set_alpha(_alpha)
            screen.blit(
                self.__battle_info[i],
                (
                    screen.get_width() / 20,
                    screen.get_height() * 3 // 4
                    + self.__battle_info[i].get_height() * 1.2 * i,
                ),
            )
            if i == 1:
                temp_seconde = self._FONT.render(
                    time.strftime(":%S", time.localtime()), linpg.colors.WHITE
                )
                temp_seconde.set_alpha(_alpha)
                screen.blit(
                    temp_seconde,
                    (
                        screen.get_width() / 20 + self.__battle_info[i].get_width(),
                        screen.get_height() * 3 // 4
                        + self.__battle_info[i].get_height() * 1.2,
                    ),
                )

    def __set_action_choice(self, choice: str | None = None) -> None:
        self.__action_choice = choice
        self.__frame_based_detection.clear()

    def __is_action_frame_event_await_trigger(self, event: str) -> bool:
        if event in self.__frame_based_detection:
            return False
        self.__frame_based_detection.add(event)
        return True

    # 把战斗系统的画面画到screen上
    def draw(self, screen: linpg.ImageSurface) -> None:
        # 环境声音-频道1
        self.environment_sound.play()
        # 调整并更新地图大小
        if self.__zoomIntoBe != self.__zoomIn:
            if self.__zoomIntoBe < self.__zoomIn:
                self.__zoomIn -= 10
            elif self.__zoomIntoBe > self.__zoomIn:
                self.__zoomIn += 10
            self.get_map().set_tile_size(
                self._standard_tile_size * self.__zoomIn / 100,
            )
            # 根据block尺寸重新加载对应尺寸的UI
            RangeSystem.update_size(self.get_map().tile_size * 4 // 5)
            self.selectMenuUI.update()
        # 画出地图
        self._display_map(screen)
        # 对话模块
        if not self.__is_battle_mode:
            # 如果战斗有对话
            if self._is_any_dialog_playing():
                # 营造电影视觉
                self.__up_black_curtain.move_toward()
                self.__up_black_curtain.draw(screen)
                self.__down_black_curtain.move_toward()
                self.__down_black_curtain.draw(screen)
                super().draw(screen)
            # 如果战斗前无·对话
            elif self.__txt_alpha == 0:
                self.__is_battle_mode = True
        # 战斗模块
        else:
            self.play_bgm()
            # 上下滚轮-放大和缩小地图
            if linpg.controller.get_event("scroll_up") and self.__zoomIntoBe < 150:
                self.__zoomIntoBe += 10
            elif linpg.controller.get_event("scroll_down") and self.__zoomIntoBe > 50:
                self.__zoomIntoBe -= 10
            # 返回按钮
            if linpg.controller.get_event("back") or (
                linpg.controller.get_event("hard_confirm")
                and self.__whose_round is WhoseRound.player
            ):
                # 如果没有角色被选中，则展示暂停页面
                if self.characterGetClick is None:
                    self._show_pause_menu(screen)
                # 如果有角色被选中，则清除选中状态
                elif self.__is_waiting is True:
                    RangeSystem.set_visible(True)
                    self.characterGetClick = None
                    self.__set_action_choice()
                    RangeSystem.clear()
            # 玩家回合
            if self.__whose_round is WhoseRound.player:
                if linpg.controller.get_event("confirm"):
                    # 如果点击了回合结束的按钮
                    if self.__end_round_button.is_hovered() and self.__is_waiting is True:
                        self.__whose_round = WhoseRound.playerToSangvisFerris
                        self.characterGetClick = None
                        RangeSystem.set_visible(True)
                        RangeSystem.clear()
                    # 是否在显示移动范围后点击了且点击区域在移动范围内
                    elif len(self.the_route) > 0 and not RangeSystem.get_visible():
                        self.__is_waiting = False
                        RangeSystem.set_visible(True)
                        self.characterInControl.try_reduce_action_point(
                            len(self.the_route) * 2
                        )
                        self.characterInControl.move_follow(self.the_route)
                        self.the_route.clear()
                        RangeSystem.clear()
                    elif (
                        self.selectMenuUI.item_being_hovered == "attack"
                        and self.characterGetClick is not None
                    ):
                        if (
                            self.characterInControl.current_bullets > 0
                            and self.characterInControl.have_enough_action_point(5)
                        ):
                            self.__set_action_choice("attack")
                            RangeSystem.set_visible(False)
                            self.selectMenuUI.set_visible(False)
                        elif self.characterInControl.current_bullets <= 0:
                            WarningMessageSystem.add("magazine_is_empty")
                        elif not self.characterInControl.have_enough_action_point(5):
                            WarningMessageSystem.add("no_enough_ap_to_attack")
                    elif (
                        self.selectMenuUI.item_being_hovered == "move"
                        and self.characterGetClick is not None
                    ):
                        if self.characterInControl.have_enough_action_point(2):
                            self.__set_action_choice("move")
                            RangeSystem.set_visible(False)
                            self.selectMenuUI.set_visible(False)
                        else:
                            WarningMessageSystem.add("no_enough_ap_to_move")
                    elif (
                        self.selectMenuUI.item_being_hovered == "skill"
                        and self.characterGetClick is not None
                    ):
                        if self.characterInControl.have_enough_action_point(8):
                            self.__set_action_choice("skill")
                            RangeSystem.set_visible(False)
                            self.selectMenuUI.set_visible(False)
                        else:
                            WarningMessageSystem.add("no_enough_ap_to_use_skill")
                    elif (
                        self.selectMenuUI.item_being_hovered == "reload"
                        and self.characterGetClick is not None
                    ):
                        if (
                            self.characterInControl.have_enough_action_point(5)
                            and self.characterInControl.bullets_carried > 0
                        ):
                            self.__set_action_choice("reload")
                            RangeSystem.set_visible(False)
                            self.selectMenuUI.set_visible(False)
                        elif self.characterInControl.bullets_carried <= 0:
                            WarningMessageSystem.add("no_bullets_left")
                        elif not self.characterInControl.have_enough_action_point(5):
                            WarningMessageSystem.add("no_enough_ap_to_reload")
                    elif (
                        self.selectMenuUI.item_being_hovered == "rescue"
                        and self.characterGetClick is not None
                    ):
                        if self.characterInControl.have_enough_action_point(8):
                            self.__set_action_choice("rescue")
                            RangeSystem.set_visible(False)
                            self.selectMenuUI.set_visible(False)
                        else:
                            WarningMessageSystem.add("no_enough_ap_to_rescue")
                    elif (
                        self.selectMenuUI.item_being_hovered == "interact"
                        and self.characterGetClick is not None
                    ):
                        if self.characterInControl.have_enough_action_point(2):
                            self.__set_action_choice("interact")
                            RangeSystem.set_visible(False)
                            self.selectMenuUI.set_visible(False)
                        else:
                            WarningMessageSystem.add("no_enough_ap_to_interact")
                    # 攻击判定
                    elif (
                        self.__action_choice == "attack"
                        and not RangeSystem.get_visible()
                        and self.characterGetClick is not None
                        and len(self.enemiesGetAttack) > 0
                    ):
                        self.characterInControl.try_reduce_action_point(5)
                        self.characterInControl.notice()
                        self.characterInControl.set_action("attack", False)
                        self.__is_waiting = False
                        RangeSystem.set_visible(True)
                        RangeSystem.clear()
                    # 技能
                    elif (
                        self.__action_choice == "skill"
                        and not RangeSystem.get_visible()
                        and self.characterGetClick is not None
                        and len(self.__skill_target) > 0
                    ):
                        for key in self.__skill_target:
                            if key in self.alliances:
                                self.characterInControl.set_flip_based_on_pos(
                                    self.alliances[key].get_pos()
                                )
                            elif key in self.enemies:
                                self.characterInControl.notice()
                                self.characterInControl.set_flip_based_on_pos(
                                    self.enemies[key].get_pos()
                                )
                        self.characterInControl.try_reduce_action_point(8)
                        self.characterInControl.play_sound("skill")
                        self.characterInControl.set_action("skill", False)
                        self.__is_waiting = False
                        RangeSystem.set_visible(True)
                        RangeSystem.clear()
                    elif (
                        self.__action_choice == "rescue"
                        and not RangeSystem.get_visible()
                        and self.characterGetClick is not None
                        and self.friendGetHelp is not None
                    ):
                        self.characterInControl.try_reduce_action_point(8)
                        self.characterInControl.notice()
                        self.alliances[self.friendGetHelp].heal(1)
                        self.characterGetClick = None
                        self.__set_action_choice()
                        self.__is_waiting = True
                        RangeSystem.set_visible(True)
                        RangeSystem.clear()
                        self.__check_entity_env_interaction(self.friendGetHelp)
                    elif (
                        self.__action_choice == "interact"
                        and not RangeSystem.get_visible()
                        and self.characterGetClick is not None
                        and self.__decorationGetClick >= 0
                    ):
                        self.characterInControl.try_reduce_action_point(2)
                        theDecorationGetClick = self.__thingsCanReact[
                            self.__decorationGetClick
                        ]
                        if isinstance(theDecorationGetClick, CampfireObject):
                            theDecorationGetClick.interact()
                        self.characterGetClick = None
                        self.__set_action_choice()
                        self.__is_waiting = True
                        RangeSystem.set_visible(True)
                        RangeSystem.clear()
                    # 判断是否有被点击的角色
                    elif self._tile_is_hovering is not None:
                        for key in self.alliances:
                            if (
                                linpg.coordinates.is_same(
                                    self.alliances[key], self._tile_is_hovering
                                )
                                and self.__is_waiting is True
                                and self.alliances[key].is_alive()
                                and RangeSystem.get_visible()
                            ):
                                self._screen_to_move_speed_x = None
                                self._screen_to_move_speed_y = None
                                RangeSystem.clear()
                                if self.characterGetClick != key:
                                    self.alliances[key].play_sound("get_click")
                                    self.characterGetClick = key
                                self.__characterInfoBoard.update()
                                self.friendsCanSave = [
                                    key2
                                    for key2 in self.alliances
                                    if self.alliances[key2].is_dying()
                                    and self.alliances[key].near(self.alliances[key2])
                                ]
                                self.__thingsCanReact.clear()
                                index = 0
                                for decoration in self.get_map().decorations:
                                    if decoration.type == "campfire" and self.alliances[
                                        key
                                    ].near(decoration):
                                        self.__thingsCanReact.append(decoration)
                                    index += 1
                                self.selectMenuUI.set_visible(True)
                                break
                self.the_route.clear()
                # 选择菜单的判定，显示功能在角色动画之后
                if self.selectMenuUI.is_visible() and self.characterGetClick is not None:
                    # 移动画面以使得被点击的角色可以被更好的操作
                    tempX, tempY = self.get_map().calculate_position(
                        self.characterInControl.x, self.characterInControl.y
                    )
                    if self._screen_to_move_speed_x is None:
                        if (
                            tempX < screen.get_width() // 5
                            and self.get_map().get_local_x() <= 0
                        ):
                            self._screen_to_move_speed_x = screen.get_width() // 5 - tempX
                        elif (
                            tempX > screen.get_width() * 4 // 5
                            and self.get_map().get_local_x()
                            >= self.get_map().column * self.get_map().tile_width * -1
                        ):
                            self._screen_to_move_speed_x = (
                                screen.get_width() * 4 // 5 - tempX
                            )
                    if self._screen_to_move_speed_y is None:
                        if (
                            tempY < screen.get_height() // 5
                            and self.get_map().get_local_y() <= 0
                        ):
                            self._screen_to_move_speed_y = (
                                screen.get_height() // 5 - tempY
                            )
                        elif (
                            tempY > screen.get_height() * 4 // 5
                            and self.get_map().get_local_y()
                            >= self.get_map().row * self.get_map().tile_height * -1
                        ):
                            self._screen_to_move_speed_y = int(
                                screen.get_height() * 4 // 5 - tempY
                            )
                # 显示攻击/移动/技能范围
                if not RangeSystem.get_visible() and self.characterGetClick is not None:
                    # 显示移动范围
                    if self.__action_choice == "move":
                        if self._tile_is_hovering is not None:
                            # 根据行动值计算最远可以移动的距离
                            max_blocks_can_move = (
                                self.characterInControl.current_action_point // 2
                            )
                            self.the_route = self.get_map().find_path(
                                self.characterInControl.get_coordinate(),
                                self._tile_is_hovering,
                                self.alliances,
                                self.enemies,
                                lenMax=max_blocks_can_move,
                            )
                            RangeSystem.set_positions(0, self.the_route)
                            if len(self.the_route) > 0:
                                # 显示路径
                                xTemp, yTemp = self.get_map().calculate_position(
                                    self.the_route[-1][0], self.the_route[-1][1]
                                )
                                screen.blit(
                                    self._FONT.render(
                                        str(len(self.the_route) * 2), linpg.colors.WHITE
                                    ),
                                    (
                                        xTemp + self._FONT.size * 2,
                                        yTemp + self._FONT.size,
                                    ),
                                )
                                self.characterInControl.render(
                                    screen, self.get_map(), (xTemp, yTemp), action="move"
                                )
                    # 显示攻击范围
                    elif self.__action_choice == "attack":
                        RangeSystem.update_attack_range(
                            self.characterInControl.get_effective_range_coordinates(
                                self.get_map()
                            )
                        )
                        if self._tile_is_hovering is not None:
                            self.enemiesGetAttack.clear()
                            _attack_coverage_area: list[tuple[int, int]] = (
                                self.characterInControl.get_attack_coverage_coordinates(
                                    self._tile_is_hovering[0],
                                    self._tile_is_hovering[1],
                                    self.get_map(),
                                )
                            )
                            if len(_attack_coverage_area) > 0:
                                RangeSystem.set_positions(4, _attack_coverage_area)
                                for enemies in self.enemies:
                                    if (
                                        self.enemies[enemies].pos in _attack_coverage_area
                                        and self.enemies[enemies].is_alive()
                                    ):
                                        self.enemiesGetAttack[enemies] = (
                                            self.characterInControl.range_target_in(
                                                self.enemies[enemies]
                                            )
                                        )
                    # 显示技能范围
                    elif self.__action_choice == "skill":
                        RangeSystem.update_attack_range(
                            self.characterInControl.get_skill_effective_range_coordinates(
                                self.get_map()
                            )
                        )
                        if self._tile_is_hovering is not None:
                            _skill_coverage_area = (
                                self.characterInControl.get_skill_coverage_coordinates(
                                    self._tile_is_hovering[0],
                                    self._tile_is_hovering[1],
                                    self.get_map(),
                                )
                            )
                            RangeSystem.set_positions(4, _skill_coverage_area)
                            self.__skill_target = (
                                self.characterInControl.get_entity_in_skill_coverage(
                                    _skill_coverage_area, self.alliances, self.enemies
                                )
                            )
                        else:
                            self.__skill_target = tuple()
                    # 换弹
                    elif self.__action_choice == "reload":
                        bullets_to_add = self.characterInControl.is_reload_needed()
                        # 需要换弹
                        if bullets_to_add > 0:
                            # 如果角色有换弹动画，则播放角色的换弹动画
                            if self.characterInControl.get_imgId("reload") != -1:
                                self.characterInControl.set_action("reload", False)
                            # 扣去对应的行动值
                            self.characterInControl.try_reduce_action_point(5)
                            # 换弹
                            self.characterInControl.reload_magazine()
                            self.__is_waiting = True
                            self.characterGetClick = None
                            self.__set_action_choice()
                            RangeSystem.set_visible(True)
                        # 无需换弹
                        else:
                            WarningMessageSystem.add("magazine_is_full")
                            self.selectMenuUI.set_visible(True)
                    elif self.__action_choice == "rescue":
                        RangeSystem.clear()
                        self.friendGetHelp = None
                        for friendNeedHelp in self.friendsCanSave:
                            if (
                                self._tile_is_hovering is not None
                                and self._tile_is_hovering[0]
                                == int(self.alliances[friendNeedHelp].x)
                                and self._tile_is_hovering[1]
                                == int(self.alliances[friendNeedHelp].y)
                            ):
                                RangeSystem.set_positions(4, [self._tile_is_hovering])
                                self.friendGetHelp = friendNeedHelp
                            else:
                                RangeSystem.append_position(
                                    0,
                                    (
                                        round(self.alliances[friendNeedHelp].x),
                                        round(self.alliances[friendNeedHelp].y),
                                    ),
                                )
                    elif self.__action_choice == "interact":
                        RangeSystem.clear()
                        self.__decorationGetClick = -1
                        for i, _decoration in enumerate(self.__thingsCanReact):
                            if (
                                self._tile_is_hovering is not None
                                and _decoration.is_on_pos(self._tile_is_hovering)
                            ):
                                RangeSystem.set_positions(
                                    4,
                                    [
                                        (
                                            self._tile_is_hovering[0],
                                            self._tile_is_hovering[1],
                                        )
                                    ],
                                )
                                self.__decorationGetClick = i
                            else:
                                RangeSystem.append_position(
                                    0, (_decoration.x, _decoration.y)
                                )

                # 当有角色被点击时
                if self.characterGetClick is not None and not self.__is_waiting:
                    # 被点击的角色动画
                    RangeSystem.set_visible(True)
                    if self.__action_choice == "move":
                        if not self.characterInControl.is_idle():
                            # 播放脚步声
                            self._footstep_sounds.set_volume(
                                linpg.volume.get_effects() / 100.0
                            )
                            self._footstep_sounds.play()
                            # 是否需要更新
                            if self.characterInControl.just_entered_a_new_tile():
                                self.__alert_enemy_around(self.characterGetClick)
                        else:
                            self._footstep_sounds.stop()
                            self.__check_entity_env_interaction(self.characterGetClick)
                            # 玩家可以继续选择需要进行的操作
                            self.__is_waiting = True
                            self.characterGetClick = None
                            self.__set_action_choice()
                    elif self.__action_choice == "attack":
                        # 根据敌我坐标判断是否需要反转角色
                        if self.characterInControl.get_imgId(
                            "attack"
                        ) >= 0 and self.__is_action_frame_event_await_trigger(
                            f"{self.characterGetClick}_attack_0"
                        ):
                            if self._tile_is_hovering is not None:
                                self.characterInControl.set_flip_based_on_pos(
                                    self._tile_is_hovering
                                )
                            self.characterInControl.play_sound("attack")
                        # 播放射击音效
                        elif self.characterInControl.get_imgId(
                            "attack"
                        ) >= 3 and self.__is_action_frame_event_await_trigger(
                            f"{self.characterGetClick}_attack_3"
                        ):
                            AttackingSoundManager.play(self.characterInControl.kind)
                        if self.characterInControl.get_imgId(
                            "attack"
                        ) >= self.characterInControl.get_imgNum(
                            "attack"
                        ) - 2 and self.__is_action_frame_event_await_trigger(
                            f"{self.characterGetClick}_attack_last_2"
                        ):
                            for key in self.enemiesGetAttack:
                                if (
                                    linpg.numbers.get_random_int(0, 100)
                                    <= 50 + (self.enemiesGetAttack[key] + 1) * 15
                                ):
                                    the_damage = self.characterInControl.attack(
                                        self.enemies[key]
                                    )
                                    self.__damage_do_to_characters[key] = (
                                        self._FONT.render(
                                            "- {} hp".format(the_damage), linpg.colors.RED
                                        )
                                    )
                                    self.enemies[key].alert(100)
                                else:
                                    self.__damage_do_to_characters[key] = (
                                        self._FONT.render("Miss", linpg.colors.RED)
                                    )
                                    self.enemies[key].alert(50)
                        elif self.characterInControl.get_imgId(
                            "attack"
                        ) >= self.characterInControl.get_imgNum(
                            "attack"
                        ) - 1 and self.__is_action_frame_event_await_trigger(
                            f"{self.characterGetClick}_attack_last_1"
                        ):
                            self.characterInControl.subtract_current_bullets()
                            self.__is_waiting = True
                            self.characterGetClick = None
                            self.__set_action_choice()
                    elif self.__action_choice == "skill":
                        if self.characterInControl.get_imgId(
                            "skill"
                        ) >= self.characterInControl.get_imgNum(
                            "skill"
                        ) - 2 and self.__is_action_frame_event_await_trigger(
                            f"{self.characterGetClick}_skill_last_2"
                        ):
                            if self.characterInControl.skill_type == 0:
                                for key, value in self.characterInControl.apply_skill(
                                    self.alliances, self.enemies, self.__skill_target
                                ).items():
                                    if value > 0:
                                        self.__damage_do_to_characters[key] = (
                                            self._FONT.render(
                                                "- {} hp".format(value), linpg.colors.RED
                                            )
                                        )
                                        self.enemies[key].alert(100)
                                    else:
                                        self.__damage_do_to_characters[key] = (
                                            self._FONT.render("Miss", linpg.colors.RED)
                                        )
                                        self.enemies[key].alert(50)
                            else:
                                for key, value in self.characterInControl.apply_skill(
                                    self.alliances, self.enemies, self.__skill_target
                                ).items():
                                    self.__damage_do_to_characters[key] = (
                                        self._FONT.render(
                                            "+ {} hp".format(value), linpg.colors.GREEN
                                        )
                                    )
                        elif self.characterInControl.get_imgId(
                            "skill"
                        ) >= self.characterInControl.get_imgNum(
                            "skill"
                        ) - 1 and self.__is_action_frame_event_await_trigger(
                            f"{self.characterGetClick}_skill_last_1"
                        ):
                            self.__is_waiting = True
                            self.characterGetClick = None
                            self.__set_action_choice()
            # 敌方回合
            if self.__whose_round is WhoseRound.sangvisFerris:
                # 如果当前角色还没做出决定
                if self.enemy_instructions is None:
                    # 生成决定
                    self.enemy_instructions = self.enemyInControl.make_decision(
                        self.get_map(),
                        self.alliances,
                        self.enemies,
                        self.the_characters_detected_last_round,
                    )
                    self.__frame_based_detection.clear()
                if (
                    not len(self.enemy_instructions) == 0
                    or self.current_instruction is not None
                ):
                    # 获取需要执行的指令
                    if self.current_instruction is None:
                        self.current_instruction = self.enemy_instructions.popleft()
                        if self.current_instruction.action == "move":
                            self.enemyInControl.move_follow(
                                self.current_instruction.route
                            )
                        elif self.current_instruction.action == "attack":
                            self.enemyInControl.set_flip_based_on_pos(
                                self.alliances[self.current_instruction.target].get_pos()
                            )
                            self.enemyInControl.set_action("attack", False)
                    # 根据选择调整动画
                    if self.current_instruction.action == "move":
                        if not self.enemyInControl.is_idle():
                            self._footstep_sounds.set_volume(
                                linpg.volume.get_effects() / 100.0
                            )
                            self._footstep_sounds.play()
                        else:
                            self._footstep_sounds.stop()
                            self.current_instruction = None
                    elif self.current_instruction.action == "attack":
                        if self.enemyInControl.get_imgId(
                            "attack"
                        ) >= 3 and self.__is_action_frame_event_await_trigger(
                            f"{self.enemies_in_control_id}_attack_3"
                        ):
                            AttackingSoundManager.play(self.enemyInControl.kind)
                        elif (
                            self.enemyInControl.get_imgId("attack")
                            >= self.enemyInControl.get_imgNum("attack") - 1
                        ):
                            if (
                                linpg.numbers.get_random_int(0, 100)
                                <= 50 + (self.current_instruction.target_area + 1) * 15
                            ):
                                the_damage = self.enemyInControl.attack(
                                    self.alliances[self.current_instruction.target]
                                )
                                # 如果角色进入倒地或者死亡状态，则应该将times_characters_down加一
                                if not self.alliances[
                                    self.current_instruction.target
                                ].is_alive():
                                    self.__statistics.times_characters_down += 1
                                self.__damage_do_to_characters[
                                    self.current_instruction.target
                                ] = self._FONT.render(
                                    "- {} hp".format(the_damage), linpg.colors.RED
                                )
                            else:
                                self.__damage_do_to_characters[
                                    self.current_instruction.target
                                ] = self._FONT.render("Miss", linpg.colors.RED)
                            self.current_instruction = None
                else:
                    self.enemyInControl.set_action()
                    self.enemies_in_control_id += 1
                    self.enemy_instructions = None
                    self.current_instruction = None
                    if self.enemies_in_control_id >= len(self.sangvisFerris_name_list):
                        self.__whose_round = WhoseRound.sangvisFerrisToPlayer

            if self.characterGetClick is not None:
                the_coord: tuple[int, int] = self.get_map().calculate_position(
                    self.characterInControl.x, self.characterInControl.y
                )
                # 显示选择菜单
                self.selectMenuUI.draw(
                    screen,
                    self.get_map().tile_size // 10,
                    {
                        "xStart": the_coord[0],
                        "xEnd": the_coord[0] + self.get_map().tile_size,
                        "yStart": the_coord[1],
                        "yEnd": the_coord[1] + self.get_map().tile_size // 2,
                    },
                    self.characterInControl.kind,
                    self.friendsCanSave,
                    self.__thingsCanReact,
                )
                # 左下角的角色信息
                if self.selectMenuUI.is_visible():
                    self.__characterInfoBoard.draw(screen, self.characterInControl)

            # 移除电影视觉
            self.__up_black_curtain.move_back()
            self.__up_black_curtain.draw(screen)
            self.__down_black_curtain.move_back()
            self.__down_black_curtain.draw(screen)
            # 检测回合是否结束
            if (
                self.__whose_round is WhoseRound.playerToSangvisFerris
                or self.__whose_round is WhoseRound.sangvisFerrisToPlayer
            ):
                if self.__RoundSwitchUI is not None and self.__RoundSwitchUI.draw(
                    screen, self.__whose_round, self.__statistics.total_rounds
                ):
                    if self.__whose_round is WhoseRound.playerToSangvisFerris:
                        self.enemies_in_control_id = 0
                        self.sangvisFerris_name_list.clear()
                        any_is_alert = False
                        for key in self.enemies:
                            if self.enemies[key].is_alive():
                                self.sangvisFerris_name_list.append(key)
                                if self.enemies[key].is_alert:
                                    any_is_alert = True
                        # if there are still enemies left
                        if len(self.sangvisFerris_name_list) > 0:
                            # 如果有一个铁血角色已经处于完全察觉的状态，则让所有铁血角色进入警觉状态
                            if any_is_alert:
                                for key in self.enemies:
                                    self.enemies[key].alert(100)
                            # 让倒地的角色更接近死亡
                            for key in self.alliances:
                                if self.alliances[key].is_dying():
                                    self.alliances[key].get_closer_to_death()
                            # 现在是铁血的回合！
                            self.__whose_round = WhoseRound.sangvisFerris
                        # if all enemies are eliminated
                        else:
                            self.__whose_round = WhoseRound.sangvisFerrisToPlayer
                    elif self.__whose_round is WhoseRound.sangvisFerrisToPlayer:
                        for key in self.alliances:
                            self.alliances[key].reset_action_point()
                            if not self.alliances[key].is_detected:
                                value_reduce = self.alliances[key].detection * 3 // 10
                                if value_reduce < 15:
                                    value_reduce = 15
                                self.alliances[key].notice(0 - value_reduce)
                        for key in self.enemies:
                            if not self.enemies[key].is_alert:
                                value_reduce = self.enemies[key].vigilance // 5
                                if value_reduce < 10:
                                    value_reduce = 10
                                self.enemies[key].alert(0 - value_reduce)
                        # 更新可视区域
                        self._update_darkness()
                        # 到你了，Good luck, you need it!
                        self.__whose_round = WhoseRound.player
                        self.__statistics.total_rounds += 1
                        # 更新当前回合文字
                        self.__update_current_round_text()

            # 检测玩家是否胜利或失败
            """检测失败条件"""
            # 如果全部友方倒下
            if not any(e.is_alive() for e in self.alliances.values()):
                self.__whose_round = WhoseRound.result_fail
            # 如果有回合限制
            _round_limitation: int = self.__mission_objectives.get("round_limitation", -1)
            if (
                _round_limitation > 0
                and self.__statistics.total_rounds > _round_limitation
            ):
                self.__whose_round = WhoseRound.result_fail
            # 如果不允许失去任何一位同伴
            if not self.__mission_objectives.get("allow_any_one_die", False):
                for character in self.alliances:
                    if self.alliances[character].is_dead():
                        self.__whose_round = WhoseRound.result_fail
                        break
            """检测胜利条件"""
            if self.__is_battle_mode is True:
                mission_objective_t: str = self.__mission_objectives["type"]
                # 歼灭模式
                if mission_objective_t == "annihilation":
                    annihilation_target: Optional[str | Sequence] = (
                        self.__mission_objectives.get("target")
                    )
                    # 检测是否所有敌人都已经被消灭
                    if annihilation_target is None:
                        if len(self.enemies) == 0:
                            self.characterGetClick = None
                            RangeSystem.set_visible(False)
                            self.__whose_round = WhoseRound.result_win
                        else:
                            pass
                    # 检测是否特定敌人已经被消灭
                    elif (
                        isinstance(annihilation_target, str)
                        and annihilation_target not in self.enemies
                    ):
                        self.__whose_round = WhoseRound.result_win
                    # 检测是否所有给定的目标都已经被歼灭
                    elif isinstance(annihilation_target, Sequence):
                        find_one = False
                        for key in self.alliances:
                            if key in annihilation_target:
                                find_one = True
                                break
                        if not find_one:
                            self.__whose_round = WhoseRound.result_win
                # 营救模式
                elif mission_objective_t == "rescue":
                    rescue_target: str = str(self.__mission_objectives["target"])
                    if self.alliances[rescue_target].current_hp > 0:
                        self.characterGetClick = None
                        RangeSystem.set_visible(False)
                        self.__whose_round = WhoseRound.result_win
            """开发使用"""
            if linpg.global_variables.try_get_str("endBattleAs") == "win":
                self.__whose_round = WhoseRound.result_win
                linpg.global_variables.remove("endBattleAs")
            elif linpg.global_variables.try_get_str("endBattleAs") == "lose":
                self.__whose_round = WhoseRound.result_fail
                linpg.global_variables.remove("endBattleAs")

            # 显示警告
            WarningMessageSystem.draw(screen)

            # 结束动画--胜利
            if self.__whose_round is WhoseRound.result_win:
                # 更新战后总结的数据栏
                if not ScoreBoard.is_updated():
                    self.__statistics.total_time = int(
                        time.time() - self.__statistics.starting_time
                    )
                    _rate: str = "S"
                    if self.__statistics.times_characters_down > 0:
                        _rate = "A"
                    ScoreBoard.update(
                        random.choice(list(self.alliances.values())).type,
                        self._chapter_id,
                        self._get_level_info().get(
                            "title", linpg.lang.get_text("Global", "no_translation")
                        ),
                        True,
                        self.__statistics,
                        _rate,
                    )
                if linpg.keys.get_pressed(linpg.keys.SPACE) or linpg.controller.get_event(
                    "hard_confirm"
                ):
                    self.__is_battle_mode = False
                    self.stop()
                    main_chapter_unlock: Optional[int] = (
                        linpg.PersistentVariables.try_get_int("main_chapter_unlock")
                    )
                    if self._project_name is None:
                        max_unlock: int = max(
                            self._chapter_id,
                            main_chapter_unlock if main_chapter_unlock is not None else 0,
                        )
                        linpg.PersistentVariables.set(
                            "main_chapter_unlock", value=max_unlock
                        )
                        if max_unlock >= 1:
                            linpg.PersistentVariables.set("enable_workshop", value=True)
                    linpg.global_variables.set("currentMode", value="dialog")
                    linpg.global_variables.set("section", value="dialog_after_battle")
            # 结束动画--失败
            elif self.__whose_round is WhoseRound.result_fail:
                # 更新战后总结的数据栏
                if not ScoreBoard.is_updated():
                    self.__statistics.total_time = int(
                        time.time() - self.__statistics.starting_time
                    )
                    ScoreBoard.update(
                        random.choice(list(self.alliances.values())).type,
                        self._chapter_id,
                        self._get_level_info().get(
                            "title", linpg.lang.get_text("Global", "no_translation")
                        ),
                        False,
                        self.__statistics,
                        "C",
                    )
                if linpg.keys.get_pressed(linpg.keys.SPACE) or linpg.controller.get_event(
                    "hard_confirm"
                ):
                    linpg.media.unload()
                    parameters: tuple = (
                        self._chapter_type,
                        self._chapter_id,
                        self._project_name,
                    )
                    TurnBasedBattleSystem.__init__(self)
                    self.new(parameters[0], parameters[1], parameters[2])
                elif linpg.keys.get_pressed(linpg.keys.BACKSPACE):
                    linpg.media.unload()
                    self.stop()
                    self.__is_battle_mode = False

        # 渐变效果：一次性的
        if self.__txt_alpha is None:
            self.__txt_alpha = 250
        if self.__txt_alpha > 0:
            LoadingTitle.black_bg.set_alpha(self.__txt_alpha)
            LoadingTitle.draw(screen, self.__txt_alpha)
            self.__draw_battle_info(screen, self.__txt_alpha)
            self.__txt_alpha = max(0, self.__txt_alpha - linpg.display.get_delta_time())

        # 如果战后总结已被更新，则说明战斗结束，需要渲染战后总结到屏幕上
        if ScoreBoard.is_updated() is True:
            ScoreBoard.draw(screen)

        # 展示控制台
        _CONSOLE: Optional[linpg.Console] = linpg.global_variables.get(
            "CONSOLE", _deepcopy=False
        )
        if _CONSOLE is not None:
            _CONSOLE.draw(screen)

        # 结束回合的按钮
        if self.__whose_round is WhoseRound.player:
            self.__end_round_button.draw(screen)
            screen.blit(
                self.__end_round_txt,
                linpg.coordinates.add(
                    self.__end_round_button.pos,
                    (
                        self.__end_round_button.get_width() * 35 // 100,
                        (
                            self.__end_round_button.get_height()
                            - self.__end_round_txt.get_height()
                        )
                        // 2,
                    ),
                ),
            )
            self.__current_round_txt.draw(screen)
