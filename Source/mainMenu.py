# cython: language_level=3
from .scene import *

#主菜单系统
class MainMenu(linpg.AbstractSystem):
    def __init__(self, screen:pygame.Surface):
        #初始化系统模块
        super().__init__()
        #获取屏幕的尺寸
        window_x,window_y = screen.get_size()
        #载入页面 - 渐入
        dispaly_loading_screen(screen,0,250,int(2*linpg.display.sfpsp))
        #修改控制台的位置
        linpg.console.set_pos(window_x*0.1,window_y*0.8)
        self.main_menu_txt = linpg.get_lang('MainMenu')
        #当前不可用的菜单选项
        disabled_option = ["6_developer_team","2_dlc","4_collection"]
        #检测继续按钮是否可用
        self.continueButtonIsOn:bool = True
        if not os.path.exists("Save/save.yaml"):
            disabled_option.append("0_continue")
            self.continueButtonIsOn = False
        #加载主菜单页面的文字设置
        txt_location = int(window_x*2/3)
        font_size = linpg.get_standard_font_size("medium")*2
        txt_y = (window_y-len(self.main_menu_txt["menu_main"])*font_size)/2
        for key,txt in self.main_menu_txt["menu_main"].items():
            mode = "enable" if key not in disabled_option else "disable"
            self.main_menu_txt["menu_main"][key] = linpg.fontRenderPro(txt,mode,(txt_location,txt_y),linpg.get_standard_font_size("medium"))
            txt_y += font_size
        #加载创意工坊选择页面的文字
        self.main_menu_txt["menu_workshop_choice"]["map_editor"] = linpg.get_lang("General","map_editor")
        self.main_menu_txt["menu_workshop_choice"]["dialog_editor"] = linpg.get_lang("General","dialog_editor")
        self.main_menu_txt["menu_workshop_choice"]["back"] = linpg.get_lang("Global","back")
        txt_y = (window_y-len(self.main_menu_txt["menu_workshop_choice"])*font_size)/2
        for key,txt in self.main_menu_txt["menu_workshop_choice"].items():
            self.main_menu_txt["menu_workshop_choice"][key] = linpg.fontRenderPro(txt,"enable",(txt_location,txt_y),linpg.get_standard_font_size("medium"))
            txt_y += font_size
        #数值初始化
        self.cover_alpha:int = 0
        self.menu_type:int = 0
        self.chapter_select = []
        self.workshop_files_text = []
        self.current_selected_workshop_project = None
        #退出确认
        self.exit_confirm_menu = linpg.Message(
            self.main_menu_txt["other"]["tip"],self.main_menu_txt["other"]["exit_confirm"],
            (self.main_menu_txt["other"]["confirm"],self.main_menu_txt["other"]["deny"]),True,return_button=1,escape_button=1
            )
        #关卡选择的封面
        self.cover_img = linpg.loadImg(r"Assets/image/covers/chapter1.png",screen.get_size())
        #音效
        self.click_button_sound = linpg.loadSound(r"Assets/sound/ui/main_menu_click_button.ogg",linpg.get_setting("Sound","sound_effects")/100.0)
        self.hover_on_button_sound = linpg.loadSound(r"Assets/sound/ui/main_menu_hover_on_button.ogg",linpg.get_setting("Sound","sound_effects")/100.0)
        self.hover_sound_play_on = None
        self.last_hover_sound_play_on = None
        #加载主菜单背景
        self.videoCapture = linpg.VedioFrame(
            "Assets/movie/SquadAR.mp4",window_x,window_y,True,True,(32,103),linpg.get_setting("Sound","background_music")/100.0
            )
        #初始化返回菜单判定参数
        linpg.set_glob_value("BackToMainMenu",False)
        #载入页面 - 渐出
        dispaly_loading_screen(screen,250,0,int(-2*linpg.display.sfpsp))
        #设置Discord状态
        if RPC is not None: RPC.update(state=linpg.get_lang("DiscordStatus","staying_at_main_menu"),large_image=LARGE_IMAGE)
    #当前在Data/workshop文件夹中可以读取的文件夹的名字（font的形式）
    def __reload_workshop_files_list(self, screen_size:tuple, createMode:bool=False) -> None:
        self.workshop_files = []
        self.workshop_files_text = []
        #是否需要显示“新增”选项
        if createMode: self.workshop_files.append(self.main_menu_txt["other"]["new_project"])
        for path in glob.glob(r"Data/workshop/*"):
            try:
                info_data = linpg.loadConfig(os.path.join(path,"info.yaml"))
            except:
                info_data = linpg.loadConfig("Data/info_example.yaml")
                info_data["default_lang"] = linpg.get_setting("Language")
                linpg.saveConfig(os.path.join(path,"info.yaml"),info_data)
            self.workshop_files_text.append(os.path.basename(path))
            self.workshop_files.append(info_data["title"][linpg.get_setting("Language")])
        self.workshop_files.append(linpg.get_lang("Global","back"))
        txt_location:int = int(screen_size[0]*2/3)
        txt_y:int = int((screen_size[1]-len(self.workshop_files)*linpg.get_standard_font_size("medium")*2)/2)
        for i in range(len(self.workshop_files)):
            self.workshop_files[i] = linpg.fontRenderPro(self.workshop_files[i],"enable",(txt_location,txt_y),linpg.get_standard_font_size("medium"))
            txt_y += linpg.get_standard_font_size("medium")*2
    #获取章节id
    def __get_chapter_title(self, chapterType:str, chapterId:int) -> str:
        return "{0}: {1}".format(
            linpg.get_lang("Battle_UI","numChapter").format(linpg.get_num_in_local_text(chapterId)),
            #读取dialog文件中的title
            linpg.loadConfig(
                os.path.join("Data", chapterType, "chapter{0}_dialogs_{1}.yaml".format(chapterId, linpg.get_setting("Language"))
                    ) if chapterType == "main_chapter" else os.path.join(
                        "Data", chapterType, self.current_selected_workshop_project,
                        "chapter{0}_dialogs_{1}.yaml".format(chapterId, linpg.get_setting("Language"))
                        ),
                "title"
                )
            )
    #重新加载章节选择菜单的选项
    def __reload_chapter_select_list(self, screen_size:tuple, chapterType:str="main_chapter", createMode:bool=False) -> None:
        self.chapter_select = []
        #是否需要显示“新增”选项
        if createMode: self.chapter_select.append(self.main_menu_txt["other"]["new_chapter"])
        #历遍路径下的所有章节文件
        for path in glob.glob(
            os.path.join("Data",chapterType,"*_map.yaml") if chapterType == "main_chapter" \
            else os.path.join("Data",chapterType,self.current_selected_workshop_project,"*_map.yaml")
            ): self.chapter_select.append(self.__get_chapter_title(chapterType,self.__find_chapter_id(path)))
        #将返回按钮放到菜单列表中
        self.chapter_select.append(linpg.get_lang("Global","back"))
        txt_y:int = int((screen_size[1]-len(self.chapter_select)*linpg.get_standard_font_size("medium")*2)/2)
        txt_x:int = int(screen_size[0]*2/3)
        #将菜单列表中的文字转换成文字surface
        for i in range(len(self.chapter_select)):
            """
            if chapter is unlocked or this is back button:
                mode = "enable"
            else:
                mode = "disable"
            """
            mode = "enable"
            self.chapter_select[i] = linpg.fontRenderPro(self.chapter_select[i],mode,(txt_x,txt_y),linpg.get_standard_font_size("medium"))
            txt_y += linpg.get_standard_font_size("medium")*2
    #画出文字按钮
    def __draw_buttons(self, screen:pygame.Surface) -> None:
        i:int = 0
        #主菜单
        if self.menu_type == 0:
            for button in self.main_menu_txt["menu_main"].values():
                button.draw(screen)
                if linpg.isHover(button): self.hover_sound_play_on = i
                i+=1
        #选择主线的章节
        elif self.menu_type == 1:
            for button in self.chapter_select:
                button.draw(screen)
                if linpg.isHover(button): self.hover_sound_play_on = i
                i+=1
        #创意工坊选择菜单
        elif self.menu_type == 2:
            for button in self.main_menu_txt["menu_workshop_choice"].values():
                button.draw(screen)
                if linpg.isHover(button): self.hover_sound_play_on = i
                i+=1
        #展示合集 （3-游玩，4-地图编辑器，5-对话编辑器）
        elif 5 >= self.menu_type >= 3:
            for button in self.workshop_files:
                button.draw(screen)
                if linpg.isHover(button): self.hover_sound_play_on = i
                i+=1
        #选择章节（6-游玩，7-地图编辑器，8-对话编辑器）
        elif 8 >= self.menu_type >= 6:
            for button in self.chapter_select:
                button.draw(screen)
                if linpg.isHover(button): self.hover_sound_play_on = i
                i+=1
        #播放按钮的音效
        if self.last_hover_sound_play_on != self.hover_sound_play_on:
            self.hover_on_button_sound.play()
            self.last_hover_sound_play_on = self.hover_sound_play_on
    #为新的创意工坊项目创建一个模板
    def __create_new_project(self) -> None:
        #如果创意工坊的文件夹目录不存在，则创建一个
        if not os.path.exists("Data/workshop"): os.makedirs("Data/workshop")
        #生成名称
        fileDefaultName = "example"
        avoidDuplicateId = 1
        fileName = fileDefaultName
        #循环确保名称不重复
        while os.path.exists(os.path.join("Data", "workshop", fileName)):
            fileName = "{0} ({1})".format(fileDefaultName,avoidDuplicateId)
            avoidDuplicateId += 1
        #创建文件夹
        os.makedirs(os.path.join("Data","workshop",fileName))
        #储存数据
        info_data:dict = linpg.loadConfig("Data/info_example.yaml")
        info_data["default_lang"] = linpg.get_setting("Language")
        linpg.saveConfig(os.path.join("Data","workshop",fileName,"info.yaml"),info_data)
    #创建新的对话文和地图文件
    def __create_new_chapter(self) -> None:
        chapterId:int = len(glob.glob(os.path.join(
            "Data", "workshop", self.current_selected_workshop_project, "*_dialogs_{}.yaml".format(linpg.get_setting("Language"))
            ))) + 1
        #复制视觉小说系统默认模板
        shutil.copyfile(
            "Data/chapter_dialogs_example.yaml",
            os.path.join(
                "Data", "workshop", self.current_selected_workshop_project,
                "chapter{0}_dialogs_{1}.yaml".format(chapterId, linpg.get_setting("Language"))
                )
            )
        #复制战斗系统默认模板
        shutil.copyfile(
            "Data/chapter_map_example.yaml",
            os.path.join("Data", "workshop", self.current_selected_workshop_project, "chapter{}_map.yaml".format(chapterId))
        )
    #根据路径判定章节的Id
    def __find_chapter_id(self, path:str) -> int:
        fileName = os.path.basename(path)
        if fileName[0:7] == "chapter":
            return int(fileName[7:fileName.index('_')])
        else:
            raise Exception('Error: Cannot find the id of chapter because the file is not properly named!')
    #加载章节
    def __load_scene(self, chapterType:str, chapterId:int, screen:pygame.Surface) -> None:
        if RPC is not None: RPC.update(
            details = linpg.get_lang('General','main_chapter') if chapterType == "main_chapter" else linpg.get_lang('General','workshop'),
            state = self.__get_chapter_title(chapterType,chapterId),
            large_image = LARGE_IMAGE,
            )
        self.videoCapture.stop()
        project_name = None if chapterType == "main_chapter" else self.current_selected_workshop_project
        dialog(chapterType,chapterId,screen,"dialog_before_battle",project_name)
        if not linpg.get_glob_value("BackToMainMenu"):
            battle(chapterType,chapterId,screen,project_name)
            if not linpg.get_glob_value("BackToMainMenu"):
                dialog(chapterType,chapterId,screen,"dialog_after_battle",project_name)
            else:
                linpg.set_glob_value("BackToMainMenu",False)
        else:
            linpg.set_glob_value("BackToMainMenu",False)
        self.__reset_menu()
        if RPC is not None: RPC.update(state=linpg.get_lang("DiscordStatus","staying_at_main_menu"),large_image=LARGE_IMAGE)
    #继续章节
    def __continue_scene(self, screen:pygame.Surface) -> None:
        self.videoCapture.stop()
        SAVE:dict = linpg.loadConfig("Save/save.yaml")
        if RPC is not None: RPC.update(
            details = linpg.get_lang('General','main_chapter') if SAVE["chapter_type"] == "main_chapter" else linpg.get_lang('General','workshop'),
            state = self.__get_chapter_title(SAVE["chapter_type"],SAVE["chapter_id"]),
            large_image = LARGE_IMAGE,
            )
        startPoint = SAVE["type"]
        if startPoint == "dialog_before_battle":
            dialog(None,None,screen,None)
            if not linpg.get_glob_value("BackToMainMenu"):
                battle(SAVE["chapter_type"],SAVE["chapter_id"],screen,SAVE["project_name"])
                if not linpg.get_glob_value("BackToMainMenu"):
                    dialog(SAVE["chapter_type"],SAVE["chapter_id"],screen,"dialog_after_battle",SAVE["project_name"])
                else:
                    linpg.set_glob_value("BackToMainMenu",False)
            else:
                linpg.set_glob_value("BackToMainMenu",False)
        elif startPoint == "battle":
            battle(None,None,screen)
            if not linpg.get_glob_value("BackToMainMenu"):
                dialog(SAVE["chapter_type"],SAVE["chapter_id"],screen,"dialog_after_battle",SAVE["project_name"])
            else:
                linpg.set_glob_value("BackToMainMenu",False)
        elif startPoint == "dialog_after_battle":
            dialog(None,None,screen,None)
            linpg.if_get_set_value("BackToMainMenu",True,False)
        self.__reset_menu()
        if RPC is not None: RPC.update(state=linpg.get_lang("DiscordStatus","staying_at_main_menu"),large_image=LARGE_IMAGE)
    #更新主菜单的部分元素
    def __reset_menu(self) -> None:
        self.videoCapture = self.videoCapture.copy()
        self.videoCapture.start()
        #是否可以继续游戏了（save文件是否被创建）
        if os.path.exists("Save/save.yaml") and not self.continueButtonIsOn:
            self.main_menu_txt["menu_main"]["0_continue"] = linpg.fontRenderPro(
                linpg.get_lang("MainMenu","menu_main")["0_continue"], "enable",
                self.main_menu_txt["menu_main"]["0_continue"].get_pos(), linpg.get_standard_font_size("medium")
                )
            self.continueButtonIsOn = True
        elif not os.path.exists("Save/save.yaml") and self.continueButtonIsOn is True:
            self.main_menu_txt["menu_main"]["0_continue"] = linpg.fontRenderPro(
                linpg.get_lang("MainMenu","menu_main")["0_continue"], "disable",
                self.main_menu_txt["menu_main"]["0_continue"].get_pos(), linpg.get_standard_font_size("medium")
                )
            self.continueButtonIsOn = False
    #更新音量
    def __update_sound_volume(self) -> None:
        self.click_button_sound.set_volume(linpg.get_setting("Sound","sound_effects")/100.0)
        self.hover_on_button_sound.set_volume(linpg.get_setting("Sound","sound_effects")/100.0)
        self.videoCapture.set_volume(linpg.get_setting("Sound","background_music")/100.0)
    #画出主菜单
    def draw(self, screen:pygame.Surface) -> None:
        #开始播放背景视频
        if not self.videoCapture.started: self.videoCapture.start()
        #背景视频
        self.videoCapture.draw(screen)
        #画出章节背景
        if self.menu_type == 1 and linpg.isHover(self.chapter_select[0]):
            if self.cover_alpha < 255:
                self.cover_alpha += 15
        elif self.cover_alpha >= 0:
            self.cover_alpha -= 15
        #如果图片的透明度大于10则展示图片
        if self.cover_alpha > 10:
            self.cover_img.set_alpha(self.cover_alpha)
            screen.blit(self.cover_img,(0,0))
        #菜单选项
        self.__draw_buttons(screen)
        #展示设置UI
        linpg.get_option_menu().draw(screen)
        #更新音量
        if linpg.get_option_menu().need_update is True:
            self.__update_sound_volume()
            linpg.get_option_menu().need_update = False
        #展示控制台
        linpg.console.draw(screen)
        #判断按键
        if linpg.controller.get_event() == "comfirm" and linpg.get_option_menu().hidden is True:
            self.click_button_sound.play()
            #主菜单
            if self.menu_type == 0:
                #继续游戏
                if linpg.isHover(self.main_menu_txt["menu_main"]["0_continue"]) and os.path.exists("Save/save.yaml"):
                    self.__continue_scene(screen)
                #选择章节
                elif linpg.isHover(self.main_menu_txt["menu_main"]["1_chooseChapter"]):
                    #加载菜单章节选择页面的文字
                    self.__reload_chapter_select_list(screen.get_size())
                    self.menu_type = 1
                #dlc
                elif linpg.isHover(self.main_menu_txt["menu_main"]["2_dlc"]):
                    pass
                #创意工坊
                elif linpg.isHover(self.main_menu_txt["menu_main"]["3_workshop"]):
                    self.menu_type = 2
                #收集物
                elif linpg.isHover(self.main_menu_txt["menu_main"]["4_collection"]):
                    pass
                #设置
                elif linpg.isHover(self.main_menu_txt["menu_main"]["5_setting"]):
                    linpg.get_option_menu().hidden = False
                #制作组
                elif linpg.isHover(self.main_menu_txt["menu_main"]["6_developer_team"]):
                    pass
                #退出
                elif linpg.isHover(self.main_menu_txt["menu_main"]["7_exit"]) and self.exit_confirm_menu.draw() == 0:
                    self.videoCapture.stop()
                    self.stop()
                    if RPC is not None: RPC.close()
            #选择主线章节
            elif self.menu_type == 1:
                if linpg.isHover(self.chapter_select[-1]):
                    self.menu_type = 0
                else:
                    for i in range(len(self.chapter_select)-1):
                        #章节选择
                        if linpg.isHover(self.chapter_select[i]):
                            self.__load_scene("main_chapter",i+1,screen)
                            break
            #选择创意工坊选项
            elif self.menu_type == 2:
                if linpg.isHover(self.main_menu_txt["menu_workshop_choice"]["0_play"]):
                    self.__reload_workshop_files_list(screen.get_size(),False)
                    self.menu_type = 3
                elif linpg.isHover(self.main_menu_txt["menu_workshop_choice"]["map_editor"]):
                    self.__reload_workshop_files_list(screen.get_size(),True)
                    self.menu_type = 4
                elif linpg.isHover(self.main_menu_txt["menu_workshop_choice"]["dialog_editor"]):
                    self.__reload_workshop_files_list(screen.get_size(),True)
                    self.menu_type = 5
                elif linpg.isHover(self.main_menu_txt["menu_workshop_choice"]["back"]):
                    self.menu_type = 0
            #创意工坊-选择想要游玩的合集
            elif self.menu_type == 3:
                if linpg.isHover(self.workshop_files[-1]):
                    self.menu_type = 2
                else:
                    for i in range(len(self.workshop_files)-1):
                        #章节选择
                        if linpg.isHover(self.workshop_files[i]):
                            self.current_selected_workshop_project = self.workshop_files_text[i]
                            self.__reload_chapter_select_list(screen.get_size(),"workshop")
                            self.menu_type = 6
                            break
            #创意工坊-选择想要编辑地图的合集
            elif self.menu_type == 4:
                #新建合集
                if linpg.isHover(self.workshop_files[0]):
                    self.__create_new_project()
                    self.__reload_workshop_files_list(screen.get_size(),True)
                #返回创意工坊选项菜单
                elif linpg.isHover(self.workshop_files[-1]):
                    self.menu_type = 2
                else:
                    for i in range(1,len(self.workshop_files)-1):
                        #章节选择
                        if linpg.isHover(self.workshop_files[i]):
                            self.current_selected_workshop_project = self.workshop_files_text[i-1]
                            self.__reload_chapter_select_list(screen.get_size(),"workshop",True)
                            self.menu_type = 7
                            break
            #创意工坊-选择想要编辑对话的合集
            elif self.menu_type == 5:
                #新建合集
                if linpg.isHover(self.workshop_files[0]):
                    self.__create_new_project()
                    self.__reload_workshop_files_list(screen.get_size(),True)
                #返回创意工坊选项菜单
                elif linpg.isHover(self.workshop_files[-1]):
                    self.menu_type = 2
                else:
                    for i in range(1,len(self.workshop_files)-1):
                        #章节选择
                        if linpg.isHover(self.workshop_files[i]):
                            self.current_selected_workshop_project = self.workshop_files_text[i-1]
                            self.__reload_chapter_select_list(screen.get_size(),"workshop",True)
                            self.menu_type = 8
                            break
            #创意工坊-选择当前合集想要游玩的关卡
            elif self.menu_type == 6:
                if linpg.isHover(self.chapter_select[-1]):
                    self.menu_type = 3
                else:
                    for i in range(len(self.chapter_select)-1):
                        #章节选择
                        if linpg.isHover(self.chapter_select[i]):
                            self.__load_scene("workshop",i+1,screen)
                            break
            #创意工坊-选择当前合集想要编辑地图的关卡
            elif self.menu_type == 7:
                if linpg.isHover(self.chapter_select[0]):
                    self.__create_new_chapter()
                    self.__reload_chapter_select_list(screen.get_size(),"workshop",True)
                elif linpg.isHover(self.chapter_select[-1]):
                    self.menu_type = 4
                else:
                    for i in range(1,len(self.chapter_select)-1):
                        #章节选择
                        if linpg.isHover(self.chapter_select[i]):
                            self.videoCapture.stop()
                            mapEditor("workshop",i,screen,self.current_selected_workshop_project)
                            self.videoCapture = self.videoCapture.copy()
                            self.videoCapture.start()
                            break
            #创意工坊-选择当前合集想要编辑对话的关卡
            elif self.menu_type == 8:
                if linpg.isHover(self.chapter_select[0]):
                    self.__create_new_chapter()
                    self.__reload_chapter_select_list(screen.get_size(),"workshop",True)
                elif linpg.isHover(self.chapter_select[-1]):
                    self.menu_type = 5
                else:
                    for i in range(1,len(self.chapter_select)-1):
                        #章节选择
                        if linpg.isHover(self.chapter_select[i]):
                            self.videoCapture.stop()
                            dialogEditor("workshop",i,screen,"dialog_before_battle",self.current_selected_workshop_project)
                            self.videoCapture = self.videoCapture.copy()
                            self.videoCapture.start()
                            break
        ALPHA_BUILD_WARNING.draw(screen)