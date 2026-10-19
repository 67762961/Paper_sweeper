# 模板图目录索引

> 本文件由 `tools/gen_pic_readme.py` 自动生成，列出每个目录的用途与图片清单。
> 修改图片后请运行 `python tools/check_pics.py` 校验引用，并重新生成本文件。

## 目录结构

```
pic/
├── common/            # 公用元素：跨多个任务使用的通用界面元素（确定、关闭、获得奖励等）（8 张）
├── courtyard/         # 庭院：主界面本身与庭院上的功能入口（逢魔、麒麟、宴会等）（15 张）
├── signin/            # 登录收菜：邮件、每日一签、福袋、纸人、免费礼包、友情点（24 张）
├── guild/             # 结界养成：阴阳寮工资、寄养、结界卡、式神育成、食盒酒壶（42 张）
├── breakthrough/      # 结界突破（9 张）
├── digui/             # 地域鬼王（14 张）
├── fengmo/            # 逢魔之时（13 张）
├── hunt/              # 狩猎战：麒麟、阴界之门（9 张）
├── thirty/            # 寮三十：御魂协作刷本与真蛇（51 张）
├── team/              # 编队：预设编组与编队（部分由 Team_Preset 动态拼接）（16 张）
```

## `common/`（8 张）

公用元素：跨多个任务使用的通用界面元素（确定、关闭、获得奖励等）

| 图片 | 用途 | 引用模块 |
| ---- | ---- | ---- |
| `一键返回庭院.png` | 一键返回庭院 | `Lib` |
| `关闭.png` | 关闭按钮（×） | `Lib`、`Task_JiejieFight`、`Task_SignIn` |
| `拒绝协作.png` | 拒绝协作邀请 | `Lib` |
| `确定.png` | 确认按钮 | `Lib`、`Task_JiejieFight`、`Task_Shouliezhan`、`Task_SignIn`、`Task_Thirty` |
| `获得奖励.png` | 奖励获得弹窗 | `Task_Fengmo`、`Task_Jiejieyangcheng`、`Task_SignIn` |
| `退出标志1.png` | 界面退出标志 | `Lib` |
| `退出标志2.png` | 界面退出标志 | `Lib`、`Task_Jiejieyangcheng` |
| `适龄提示标.png` | 适龄提示 | `Lib` |

## `courtyard/`（15 张）

庭院：主界面本身与庭院上的功能入口（逢魔、麒麟、宴会等）

| 图片 | 用途 | 引用模块 |
| ---- | ---- | ---- |
| `主界面.png` | 庭院主界面 | `Lib` |
| `前往.png` | 前往按钮 | `Task_Fengmo` |
| `前往六道.png` | 前往按钮 | `Lib` |
| `取消退出.png` | 取消退出 | `Lib` |
| `宴会入口.png` | 庭院功能入口 | `Lib` |
| `式神录.png` | 式神录入口 | `Lib` |
| `御神.png` | 御神入口 | `Lib` |
| `斗技入口.png` | 庭院功能入口 | `Lib` |
| `狭间暗域入口.png` | 庭院功能入口 | `Lib` |
| `百鬼弈入口.png` | 庭院功能入口 | `Lib` |
| `退出游戏.png` | 退出游戏确认 | `Lib` |
| `逢魔入口.png` | 庭院功能入口 | `Lib` |
| `道馆入口.png` | 庭院功能入口 | `Lib` |
| `阴阳术.png` | 阴阳术入口 | `Lib` |
| `麒麟入口.png` | 庭院功能入口 | `Lib` |

## `signin/`（24 张）

登录收菜：邮件、每日一签、福袋、纸人、免费礼包、友情点

| 图片 | 用途 | 引用模块 |
| ---- | ---- | ---- |
| `BUFF小纸人.png` | 小纸人领取 | `Task_SignIn` |
| `一键收取.png` | 一键收取 | `Task_SignIn` |
| `一键祝福.png` | 祝福 | `Task_SignIn` |
| `万华牌跳过.png` | 万华牌跳过 | `Task_SignIn` |
| `体力小纸人.png` | 小纸人领取 | `Task_SignIn` |
| `免费礼包.png` | 免费礼包 | `Task_SignIn` |
| `全部领取.png` | 全部领取 | `Task_SignIn` |
| `全部领取界面.png` | 全部领取 | `Task_SignIn` |
| `勾玉小纸人.png` | 小纸人领取 | `Task_SignIn` |
| `友情点切换.png` | 友情点切换 | `Task_SignIn` |
| `吉闻.png` | 吉闻界面 | `Task_SignIn` |
| `商店.png` | 商店入口 | `Task_SignIn` |
| `好友.png` | 好友界面 | `Task_SignIn` |
| `日常.png` | 日常分类 | `Task_SignIn` |
| `每日一签.png` | 每日签到 | `Task_SignIn` |
| `消息邮件.png` | 邮件入口 | `Task_SignIn` |
| `礼包屋.png` | 礼包屋入口 | `Task_SignIn` |
| `礼包屋1.png` | 礼包屋入口 | `Task_SignIn` |
| `祝福.png` | 祝福 | `Task_SignIn` |
| `福袋小纸人.png` | 小纸人领取 | `Task_SignIn` |
| `签到小纸人.png` | 小纸人领取 | `Task_SignIn` |
| `解签小纸人.png` | 小纸人领取 | `Task_SignIn` |
| `邮件.png` | 邮件入口 | `Task_SignIn` |
| `邮箱.png` | 邮箱界面 | `Task_SignIn` |

## `guild/`（42 张）

结界养成：阴阳寮工资、寄养、结界卡、式神育成、食盒酒壶

| 图片 | 用途 | 引用模块 |
| ---- | ---- | ---- |
| `五星太鼓.png` | 太鼓结界卡 | `Task_Jiejieyangcheng` |
| `五星斗鱼.png` | 斗鱼结界卡 | `Task_Jiejieyangcheng` |
| `体力工资.png` | 体力工资 | `Task_Jiejieyangcheng` |
| `体力食盒.png` | 体力食盒 | `Task_Jiejieyangcheng` |
| `全部.png` | 全部列表 | `Task_Jiejieyangcheng` |
| `六星太鼓.png` | 太鼓结界卡 | `Task_Jiejieyangcheng` |
| `六星斗鱼.png` | 斗鱼结界卡 | `Task_Jiejieyangcheng` |
| `关闭弹窗.png` | 关闭按钮（×） | `Task_Jiejieyangcheng` |
| `取出.png` | 取出按钮 | `Task_Jiejieyangcheng` |
| `太鼓列表.png` | 太鼓列表 | `Task_Jiejieyangcheng` |
| `奉为达摩.png` | 达摩素材 | `Task_Jiejieyangcheng` |
| `好友.png` | 好友界面 | `Task_Jiejieyangcheng` |
| `寄养入口.png` | 庭院功能入口 | `Task_Jiejieyangcheng` |
| `寄养列表.png` | 寄养 | `Task_Jiejieyangcheng` |
| `寄养列表末尾.png` | 寄养 | `Task_Jiejieyangcheng` |
| `寄养经验.png` | 寄养 | `Task_Jiejieyangcheng` |
| `式神育成.png` | 式神育成 | `Task_Jiejieyangcheng` |
| `提取.png` | 提取按钮 | `Task_Jiejieyangcheng` |
| `放入式神.png` | 放入式神 | `Task_Jiejieyangcheng` |
| `斗鱼列表.png` | 斗鱼列表 | `Task_Jiejieyangcheng` |
| `星级降序.png` | 星级降序 | `Task_Jiejieyangcheng` |
| `有寄养位.png` | 寄养 | `Task_Jiejieyangcheng` |
| `满级达摩.png` | 达摩素材 | `Task_Jiejieyangcheng` |
| `激活.png` | 激活 | `Task_Jiejieyangcheng` |
| `确定.png` | 确认按钮 | `Task_Jiejieyangcheng` |
| `素材.png` | 素材列表 | `Task_Jiejieyangcheng` |
| `经验酒壶.png` | 经验酒壶 | `Task_Jiejieyangcheng` |
| `经验酒壶满.png` | 经验酒壶 | `Task_Jiejieyangcheng` |
| `结界.png` |  | `Task_Jiejieyangcheng` |
| `结界卡.png` | 结界卡 | `Task_Jiejieyangcheng` |
| `结界卡列表.png` | 结界卡 | `Task_Jiejieyangcheng` |
| `结界卡奖励.png` | 结界卡 | `Task_Jiejieyangcheng` |
| `结界卡槽.png` | 结界卡 | `Task_Jiejieyangcheng` |
| `结界卡运行中.png` | 结界卡 | `Task_Jiejieyangcheng` |
| `育成列表框.png` | 育成列表框 | `Task_Jiejieyangcheng` |
| `跨区.png` | 跨区 | `Task_Jiejieyangcheng` |
| `进入结界.png` | 进入结界 | `Task_Jiejieyangcheng` |
| `邀请.png` | 邀请 | `Task_Jiejieyangcheng` |
| `金币工资.png` | 金币工资 | `Task_Jiejieyangcheng` |
| `阴阳寮.png` | 阴阳寮 | `Lib` |
| `领取.png` | 领取按钮 | `Task_Jiejieyangcheng` |
| `首张结界卡.png` | 结界卡 | `Task_Jiejieyangcheng` |

## `breakthrough/`（9 张）

结界突破

| 图片 | 用途 | 引用模块 |
| ---- | ---- | ---- |
| `今日不再提醒.png` |  | `Task_JiejieFight` |
| `再次挑战.png` | 挑战按钮 | `Task_JiejieFight` |
| `刷新.png` |  | `Task_JiejieFight` |
| `勋章.png` |  | `Task_JiejieFight` |
| `已攻破结界.png` |  | `Task_JiejieFight` |
| `目标结界.png` |  | `Task_JiejieFight` |
| `结束奖励.png` |  | `Task_JiejieFight` |
| `结界突破图标.png` |  | `Task_JiejieFight` |
| `进攻.png` |  | `Task_JiejieFight` |

## `digui/`（14 张）

地域鬼王

| 图片 | 用途 | 引用模块 |
| ---- | ---- | ---- |
| `今日挑战.png` | 今日挑战 | `Task_Digui` |
| `准备.png` | 准备按钮 | `Task_Digui`、`Task_Shouliezhan` |
| `地鬼图标.png` | 地域鬼王入口 | `Lib`、`Task_Digui` |
| `战斗奖励.png` | 战斗奖励 | `Task_Digui`、`Task_Thirty` |
| `挑战.png` | 挑战按钮 | `Task_Digui` |
| `最新.png` | 最新排序 | `Task_Digui` |
| `最新挑战.png` | 挑战按钮 | `Task_Digui` |
| `未选择.png` | 未选择状态 | `Task_Digui` |
| `热门.png` | 热门排序 | `Task_Digui` |
| `第一个.png` | 第一个目标 | `Task_Digui` |
| `第三个.png` | 第三个目标 | `Task_Digui` |
| `第二个.png` | 第二个目标 | `Task_Digui` |
| `筛选.png` | 筛选 | `Task_Digui` |
| `胜利.png` | 胜利结算 | `Task_Digui` |

## `fengmo/`（13 张）

逢魔之时

| 图片 | 用途 | 引用模块 |
| ---- | ---- | ---- |
| `定位.png` | 定位按钮 | `Task_Fengmo` |
| `现世逢魔.png` | 现世逢魔 | `Task_Fengmo` |
| `逢魔图标.png` | 逢魔图标 | `Task_Fengmo` |
| `逢魔奖励.png` | 逢魔奖励 | `Task_Fengmo` |
| `逢魔奖励已领取.png` | 领取按钮 | `Task_Fengmo` |
| `逢魔极.png` | 逢魔-极 | `Task_Fengmo` |
| `逢魔次数.png` | 逢魔次数 | `Task_Fengmo` |
| `阵容预设.png` | 阵容预设 | `Task_Fengmo` |
| `集结.png` | 集结 | `Task_Fengmo` |
| `集结0.png` | 集结 | `Task_Fengmo` |
| `集结挑战.png` | 挑战按钮 | `Task_Fengmo` |
| `集结挑战1.png` | 挑战按钮 | `Task_Fengmo` |
| `首领.png` | 首领 | `Task_Fengmo` |

## `hunt/`（9 张）

狩猎战：麒麟、阴界之门

| 图片 | 用途 | 引用模块 |
| ---- | ---- | ---- |
| `前往.png` | 前往按钮 | `Task_Shouliezhan` |
| `挑战.png` | 挑战按钮 | `Task_Shouliezhan` |
| `攻打阴界之门.png` |  | `Task_Shouliezhan` |
| `组队界面挑战图标.png` | 挑战按钮 | `Task_Shouliezhan` |
| `胜利太鼓.png` | 太鼓结界卡 | `Task_Shouliezhan` |
| `阴界之门入口.png` | 庭院功能入口 | `Lib` |
| `阴界之门图标.png` |  | `Task_Shouliezhan` |
| `麒麟图标.png` |  | `Task_Shouliezhan` |
| `麒麟挑战.png` | 挑战按钮 | `Task_Shouliezhan` |

## `thirty/`（51 张）

寮三十：御魂协作刷本与真蛇

| 图片 | 用途 | 引用模块 |
| ---- | ---- | ---- |
| `关闭加成.png` | 关闭按钮（×） | `Task_Thirty` |
| `创建.png` |  | `Task_Thirty` |
| `创建队伍.png` |  | `Task_Thirty` |
| `副本组别表头.png` |  | `Task_Thirty` |
| `副本表头.png` |  | `Task_Thirty` |
| `加成.png` |  | `Task_Thirty` |
| `加成2.png` |  | `Task_Thirty` |
| `加成开启按钮.png` |  | `Task_Thirty` |
| `取消图标.png` |  | `Task_Thirty` |
| `小纸人图标.png` | 小纸人领取 | `Task_Thirty` |
| `小纸人计数.png` | 小纸人领取 | `Task_Thirty` |
| `小纸人计数0.png` | 小纸人领取 | `Task_Thirty` |
| `小纸人计数1.png` | 小纸人领取 | `Task_Thirty` |
| `小纸人计数3.png` | 小纸人领取 | `Task_Thirty` |
| `小纸人计数5.png` | 小纸人领取 | `Task_Thirty` |
| `小纸人计数确定.png` | 确认按钮 | `Task_Thirty` |
| `庭院加成.png` |  | `Task_Thirty` |
| `御魂副本组别.png` |  | `Task_Thirty` |
| `御魂加成区域.png` |  | `Task_Thirty` |
| `御魂组别选项.png` |  | `Task_Thirty` |
| `收起频道框.png` |  | `Task_Thirty` |
| `日蚀副本图标0.png` |  | `Task_Thirty` |
| `日蚀副本图标1.png` |  | `Task_Thirty` |
| `日轮之陨组别选项.png` |  | `Task_Thirty` |
| `日轮副本组别.png` |  | `Task_Thirty` |
| `永生之海四副本图标0.png` |  | `Task_Thirty` |
| `永生之海四副本图标1.png` |  | `Task_Thirty` |
| `永生之海组别.png` |  | `Task_Thirty` |
| `永生之海组别选项.png` |  | `Task_Thirty` |
| `点击加入.png` |  | `Task_Thirty` |
| `真蛇准备.png` | 准备按钮 | `Task_Thirty` |
| `真蛇图标.png` |  | `Task_Thirty` |
| `真蛇挑战.png` | 挑战按钮 | `Task_Thirty` |
| `真蛇挑战图标.png` | 挑战按钮 | `Task_Thirty` |
| `真蛇确定.png` | 确认按钮 | `Task_Thirty` |
| `真蛇自动准备.png` | 准备按钮 | `Task_Thirty` |
| `真蛇队伍创建图标.png` |  | `Task_Thirty` |
| `神罚副本图标0.png` |  | `Task_Thirty` |
| `神罚副本图标1.png` |  | `Task_Thirty` |
| `组队图标.png` |  | `Task_Thirty` |
| `自动战斗图标.png` |  | `Task_Thirty` |
| `自动战斗图标魂海.png` |  | `Task_Thirty` |
| `花车图标.png` |  | `Task_Thirty` |
| `虚无副本图标0.png` |  | `Task_Thirty` |
| `虚无副本图标1.png` |  | `Task_Thirty` |
| `退出.png` |  | `Task_Thirty` |
| `退出2.png` |  | `Task_Thirty` |
| `邀请好友和寮成员.png` | 好友界面 | `Task_Thirty` |
| `阴阳寮频道0.png` | 阴阳寮 | `Task_Thirty` |
| `阴阳寮频道1.png` | 阴阳寮 | `Task_Thirty` |
| `频道.png` |  | `Task_Thirty` |

## `team/`（16 张）

编队：预设编组与编队（部分由 Team_Preset 动态拼接）

| 图片 | 用途 | 引用模块 |
| ---- | ---- | ---- |
| `出战.png` | 出战按钮 | `Task_Digui` |
| `副本编组.png` | 预设编组 | （动态拼接） |
| `应用御魂预设.png` | 应用御魂预设 | `Lib` |
| `日常编组.png` | 日常分类 | （动态拼接） |
| `日常编组按钮.png` | 日常分类 | `Task_Digui` |
| `日轮编队.png` | 预设编队 | （动态拼接） |
| `真蛇编队.png` | 预设编队 | （动态拼接） |
| `结界编队.png` | 预设编队 | （动态拼接） |
| `结界队出战.png` | 出战按钮 | `Task_Digui` |
| `预设登陆.png` | 预设入口 | `Task_Digui` |
| `预设登陆1.png` | 预设入口 | `Task_Digui` |
| `预设选项.png` | 预设选项 | `Lib` |
| `魂海编队.png` | 预设编队 | （动态拼接） |
| `魂王编队.png` | 预设编队 | （动态拼接） |
| `魂虚编队.png` | 预设编队 | （动态拼接） |
| `麒麟编队.png` | 预设编队 | （动态拼接） |

---

**共 201 张模板图，10 个目录。**

## 维护说明

- **新增图片**：放进对应业务目录，文件名用中文；在代码里引用后运行 `python tools/check_pics.py`。
- **改名/移动**：用 `git mv` 保留历史，同步修改代码引用，再跑 `check_pics.py`。
- **动态拼接**：`team/` 目录下的编队图由 `Lib.Team_Preset()` 用 f-string 拼接，
  路径形如 `./pic/team/{Preset_name}.png`，`check_pics.py` 会跳过该目录的死图判定。
- **中文文件名**：读取走 `Lib.Img_read_ch()`（`np.frombuffer` + `cv2.imdecode`），支持任意编码路径。
