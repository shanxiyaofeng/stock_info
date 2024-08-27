import wx
import json
import requests
import random
import keyboard

# 配置文件路径
config_file_path = "stock_hold_info.json"

# 初始化股票持有信息和窗口位置大小
hold_info = {}
window_pos = None
window_size = None
is_init = True

# 读取配置文件
try:
    with open(config_file_path, "r") as config_file:
        config_data = json.load(config_file)
        is_init = config_data.get('is_init', True)
        hold_info = config_data.get('hold_info', {})
        window_pos_tuple = config_data.get('window_pos')
        window_size_tuple = config_data.get('window_size')
        if window_pos_tuple is not None and window_size_tuple is not None:
            window_pos = wx.Point(*window_pos_tuple)  # 从元组转换回wx.Point
            window_size = wx.Size(*window_size_tuple)  # 从元组转换回wx.Size
except FileNotFoundError:
    pass  # 如果文件不存在，则使用默认值
except json.JSONDecodeError:
    hold_info = {}  # 如果文件损坏，则清空数据

# 默认情况下填充一些示例数据
if not hold_info and is_init:
    is_init = False
    hold_info = {
        'sh000001': {'name': '上证指数', 'cost': 0.0, 'hold_num': 0},
        'sz399006': {'name': '创业板指', 'cost': 0.0, 'hold_num': 0},
    }

timer_time = 1000
data_referer_list = [
    "https://gu.qq.com/",
    "https://finance.qq.com/",
    "https://proxy.finance.qq.com/"
]


class StockInfoFrame(wx.Frame):
    def __init__(self, *args, **kw):
        super(StockInfoFrame, self).__init__(*args, **kw)
        self.SetTransparent(100)
        self.panel = wx.Panel(self)
        self.list_ctrl = wx.ListCtrl(self.panel, style=wx.LC_REPORT | wx.LC_HRULES | wx.LC_VRULES)

        # 添加列标题
        self.list_ctrl.InsertColumn(0, '股票名称', width=100)
        self.list_ctrl.InsertColumn(1, '最新价格', width=68)
        self.list_ctrl.InsertColumn(2, '涨跌', width=68)
        self.list_ctrl.InsertColumn(3, '涨跌率', width=68)
        self.list_ctrl.InsertColumn(4, '盈亏', width=88)
        self.list_ctrl.InsertColumn(5, '成本', width=68)

        # 获取并显示股票数据
        self.load_data()

        # 布局
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.list_ctrl, 1, wx.EXPAND)
        self.panel.SetSizer(sizer)

        # 设置窗口位置和大小
        if window_pos is not None and window_size is not None:
            self.SetPosition(window_pos)
            self.SetSize(window_size)
        else:
            self.Centre()
            self.SetSize((480, 138))

        self.Show(True)

        self.is_hidden = False

        # 创建定时器
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_timer)
        # 绑定显示/隐藏事件
        self.Bind(wx.EVT_SHOW, self.on_show)
        # 启动定时器，每60秒（60000毫秒）刷新一次
        self.timer.Start(timer_time)

        # 添加菜单栏
        self.menu_bar = wx.MenuBar()
        edit_menu = wx.Menu()
        self.menu_bar.Append(edit_menu, "&编辑")
        self.SetMenuBar(self.menu_bar)

        # 添加编辑菜单项
        edit_menu_item = edit_menu.Append(wx.ID_EDIT, "编辑")
        self.Bind(wx.EVT_MENU, self.on_edit_button, edit_menu_item)

        # 调整大小以适应内容
        self.adjust_size_to_content()

        # 绑定窗口大小和位置改变事件
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_MOVE, self.on_move)

    def load_data(self):
        self.list_ctrl.DeleteAllItems()
        if not hold_info:
            return
        try:
            random_referer = random.choice(data_referer_list)
            headers = {
                'Accept': '*/*',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7,ja;q=0.6',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Pragma': 'no-cache',
                'Referer': random_referer,
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.114 Safari/537.36',
                'sec-ch-ua': '"Google Chrome";v="89", "Chromium";v="89", ";Not A Brand";v="99"',
                'sec-ch-ua-mobile': '?0',
                'Sec-Fetch-Dest': 'script',
                'Sec-Fetch-Mode': 'no-cors',
                'Sec-Fetch-Site': 'cross-site'
            }
            full_codes = hold_info.keys()
            res = requests.get(f'http://web.sqt.gtimg.cn/q={",".join(full_codes)}', headers=headers).text
            data_list = res.split(';')
            data_list.pop()

            for data in data_list:
                stock_data_list = data.split('~')

                # 解包提取需要的信息
                stock_code = stock_data_list[0].split('=')[0].replace('v_', '').replace('\n', '')  # 股票代码
                stock_name = stock_data_list[1]  # 股票名称
                latest_price = stock_data_list[3]  # 最新价
                change = stock_data_list[31]  # 涨跌
                change_rise = stock_data_list[32]  # 涨跌率
                profit = f"{((float(latest_price) - hold_info.get(stock_code).get('cost')) * hold_info.get(stock_code).get('hold_num')):.2f}"  # 盈亏
                cost = hold_info.get(stock_code).get('cost')  # 成本

                # 添加到列表控件中
                self.list_ctrl.Append([
                    stock_name, latest_price, change, change_rise, profit, cost
                ])

        except requests.RequestException as e:
            wx.MessageBox(f"网络请求失败: {e}", "错误", wx.OK | wx.ICON_ERROR)
        except Exception as e:
            wx.MessageBox(f"处理数据时出错: {e}", "错误", wx.OK | wx.ICON_ERROR)

    def adjust_size_to_content(self):
        # 调整大小以适应内容
        self.list_ctrl.SetSizeHints(500, 130)  # 设置为自动调整大小
        self.Fit()  # 调整窗口大小以适应内容
        self.Layout()  # 布局更新

    def on_timer(self, event):
        # 定时器触发时加载数据
        self.load_data()

    def on_show(self, event):
        # 当窗口显示状态改变时，控制定时器的启动和停止
        if self.IsShown():
            self.load_data()
            self.timer.Start(timer_time)
        else:
            self.timer.Stop()

        # 保存窗口的位置和大小
        self.save_window_pos_and_size()

    def save_window_pos_and_size(self):
        # 保存窗口的位置和大小到配置文件
        global window_pos, window_size
        window_pos = self.GetPosition()
        window_size = self.GetSize()
        config_data = {
            'hold_info': hold_info,
            'window_pos': (window_pos.x, window_pos.y),  # 将wx.Point转换为元组
            'window_size': (window_size.width, window_size.height)  # 将wx.Size转换为元组
        }
        with open(config_file_path, "w") as config_file:
            json.dump(config_data, config_file, indent=4)

    def on_edit_button(self, event):
        # 显示编辑框
        EditDialog(self).ShowModal()

    def on_size(self, event):
        # 当窗口大小改变时保存窗口大小
        self.save_window_pos_and_size()
        event.Skip()

    def on_move(self, event):
        # 当窗口位置改变时保存窗口位置
        self.save_window_pos_and_size()
        event.Skip()


class EditDialog(wx.Dialog):
    def __init__(self, parent):
        super(EditDialog, self).__init__(parent, title="编辑股票信息")

        # 设置布局
        vbox = wx.BoxSizer(wx.VERTICAL)

        self.stock_code_list = list(hold_info.keys())
        self.stock_code_choice = wx.Choice(self, choices=self.stock_code_list)
        vbox.Add(self.stock_code_choice, 0, wx.EXPAND | wx.ALL, 5)

        self.cost_text = wx.StaticText(self, label="成本:")
        vbox.Add(self.cost_text, 0, wx.ALIGN_LEFT | wx.LEFT, 10)

        self.cost_input = wx.TextCtrl(self)
        vbox.Add(self.cost_input, 0, wx.EXPAND | wx.ALL, 5)

        self.hold_num_text = wx.StaticText(self, label="持有数量:")
        vbox.Add(self.hold_num_text, 0, wx.ALIGN_LEFT | wx.LEFT, 10)

        self.hold_num_input = wx.TextCtrl(self)
        vbox.Add(self.hold_num_input, 0, wx.EXPAND | wx.ALL, 5)

        # 添加股票
        self.add_stock_text = wx.StaticText(self, label="添加股票:")
        vbox.Add(self.add_stock_text, 0, wx.ALIGN_LEFT | wx.LEFT, 10)

        self.add_stock_input = wx.TextCtrl(self)
        vbox.Add(self.add_stock_input, 0, wx.EXPAND | wx.ALL, 5)

        add_button = wx.Button(self, label="添加")
        self.Bind(wx.EVT_BUTTON, self.on_add_button, add_button)
        vbox.Add(add_button, 0, wx.EXPAND | wx.ALL, 5)

        # 删除股票
        delete_button = wx.Button(self, label="删除")
        self.Bind(wx.EVT_BUTTON, self.on_delete_button, delete_button)
        vbox.Add(delete_button, 0, wx.EXPAND | wx.ALL, 5)

        button_sizer = wx.StdDialogButtonSizer()
        ok_button = wx.Button(self, wx.ID_OK)
        ok_button.Bind(wx.EVT_BUTTON, self.on_ok_button)
        button_sizer.AddButton(ok_button)
        cancel_button = wx.Button(self, wx.ID_CANCEL)
        button_sizer.AddButton(cancel_button)
        button_sizer.Realize()
        vbox.Add(button_sizer, 0, wx.EXPAND | wx.ALL, 5)

        self.SetSizer(vbox)
        self.Fit()

        # 更新控件
        self.update_controls()

    def update_controls(self):
        selected_stock_code = self.stock_code_choice.GetStringSelection()
        if selected_stock_code:
            stock_info = hold_info[selected_stock_code]
            self.cost_input.SetValue(str(stock_info['cost']))
            self.hold_num_input.SetValue(str(stock_info['hold_num']))

    def on_ok_button(self, event):
        selected_stock_code = self.stock_code_choice.GetStringSelection()
        if selected_stock_code:
            new_cost = float(self.cost_input.GetValue())
            new_hold_num = int(self.hold_num_input.GetValue())

            # 更新 hold_info
            hold_info[selected_stock_code]['cost'] = new_cost
            hold_info[selected_stock_code]['hold_num'] = new_hold_num

            # 保存到文件
            self.save_config()

            # 关闭对话框
            self.EndModal(wx.ID_OK)

    def on_add_button(self, event):
        # 获取输入的股票代码
        stock_code = self.add_stock_input.GetValue().strip()
        if stock_code:
            # 请求股票数据
            try:
                random_referer = random.choice(data_referer_list)
                headers = {
                    'Accept': '*/*',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7,ja;q=0.6',
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
                    'Pragma': 'no-cache',
                    'Referer': random_referer,
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.114 Safari/537.36',
                    'sec-ch-ua': '"Google Chrome";v="89", "Chromium";v="89", ";Not A Brand";v="99"',
                    'sec-ch-ua-mobile': '?0',
                    'Sec-Fetch-Dest': 'script',
                    'Sec-Fetch-Mode': 'no-cors',
                    'Sec-Fetch-Site': 'cross-site'
                }
                res = requests.get(f"http://web.sqt.gtimg.cn/q={stock_code}", headers=headers).text
                data_list = res.split('~')
                stock_name = data_list[1]  # 股票名称

                # 添加股票信息
                hold_info[stock_code] = {'cost': 0.0, 'hold_num': 0}

                # 更新 hold_info 到文件
                self.save_config()

                # 更新选择框
                self.stock_code_choice.Append(stock_code)
                self.stock_code_choice.SetStringSelection(stock_code)
                self.update_controls()
            except requests.RequestException as e:
                wx.MessageBox(f"网络请求失败: {e}", "错误", wx.OK | wx.ICON_ERROR)
            except Exception as e:
                wx.MessageBox(f"处理数据时出错: {e}", "错误", wx.OK | wx.ICON_ERROR)

    def on_delete_button(self, event):
        selected_stock_code = self.stock_code_choice.GetStringSelection()
        if selected_stock_code:
            # 确认删除
            if wx.MessageDialog(self, f"确定要删除股票 {selected_stock_code} 吗?", "确认删除",
                                wx.YES_NO | wx.ICON_QUESTION).ShowModal() == wx.ID_YES:
                # 从 hold_info 中删除股票
                del hold_info[selected_stock_code]

                # 更新 hold_info 到文件
                self.save_config()

                # 更新选择框
                self.stock_code_choice.Delete(self.stock_code_choice.GetSelection())
                self.stock_code_choice.SetStringSelection("")
                self.update_controls()

    def save_config(self):
        # 保存 hold_info 到配置文件
        global window_pos, window_size
        config_data = {
            'is_init': is_init,
            'hold_info': hold_info,
            'window_pos': (window_pos.x, window_pos.y),
            'window_size': (window_size.width, window_size.height)
        }
        with open(config_file_path, "w") as config_file:
            json.dump(config_data, config_file, indent=4)

def on_global_hotkey():
    global main_frame
    if main_frame.is_hidden:
        main_frame.Show(True)
        main_frame.Raise()
        main_frame.SetFocus()
        main_frame.is_hidden = False
    else:
        main_frame.last_position = main_frame.GetPosition()
        main_frame.last_size = main_frame.GetSize()
        main_frame.Hide()
        main_frame.is_hidden = True


if __name__ == "__main__":
    app = wx.App(False)
    main_frame = StockInfoFrame(None)
    # 注册全局热键监听
    keyboard.add_hotkey('ctrl+~', on_global_hotkey, suppress=True)
    app.MainLoop()
