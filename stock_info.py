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


def load_config():
    global hold_info, window_pos, window_size, is_init
    try:
        with open(config_file_path, "r") as config_file:
            config_data = json.load(config_file)
            is_init = config_data.get('is_init', True)
            hold_info = config_data.get('hold_info', {})
            window_pos_tuple = config_data.get('window_pos')
            window_size_tuple = config_data.get('window_size')
            if window_pos_tuple and window_size_tuple:
                window_pos = wx.Point(*window_pos_tuple)
                window_size = wx.Size(*window_size_tuple)
    except FileNotFoundError:
        pass
    except json.JSONDecodeError:
        hold_info = {}


def save_config():
    global window_pos, window_size
    config_data = {
        'is_init': is_init,
        'hold_info': hold_info,
        'window_pos': (window_pos.x, window_pos.y),
        'window_size': (window_size.width, window_size.height)
    }
    with open(config_file_path, "w") as config_file:
        json.dump(config_data, config_file, indent=4)


def get_stock_data(codes):
    data_referer_list = [
        "https://gu.qq.com/",
        "https://finance.qq.com/",
        "https://proxy.finance.qq.com/"
    ]
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
        res = requests.get(f'http://web.sqt.gtimg.cn/q={",".join(codes)}', headers=headers).text
        return res.split(';')[:-1]
    except requests.RequestException as e:
        wx.MessageBox(f"网络请求失败: {e}", "错误", wx.OK | wx.ICON_ERROR)
        return []
    except Exception as e:
        wx.MessageBox(f"处理数据时出错: {e}", "错误", wx.OK | wx.ICON_ERROR)
        return []


class StockInfoFrame(wx.Frame):
    def __init__(self, *args, **kw):
        super(StockInfoFrame, self).__init__(*args, **kw)
        self.SetTransparent(100)
        self.panel = wx.Panel(self)
        self.list_ctrl = wx.ListCtrl(self.panel, style=wx.LC_REPORT | wx.LC_HRULES | wx.LC_VRULES)

        self.list_ctrl.InsertColumn(0, '股票名称', width=100)
        self.list_ctrl.InsertColumn(1, '最新价格', width=68)
        self.list_ctrl.InsertColumn(2, '涨跌', width=68)
        self.list_ctrl.InsertColumn(3, '涨跌率', width=68)
        self.list_ctrl.InsertColumn(4, '盈亏', width=88)
        self.list_ctrl.InsertColumn(5, '成本', width=68)

        self.load_data()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.list_ctrl, 1, wx.EXPAND)
        self.panel.SetSizer(sizer)

        if window_pos and window_size:
            self.SetPosition(window_pos)
            self.SetSize(window_size)
        else:
            self.Centre()
            self.SetSize((480, 138))

        self.Show(True)
        self.is_hidden = False

        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_timer)
        self.Bind(wx.EVT_SHOW, self.on_show)
        self.timer.Start(1000)

        self.menu_bar = wx.MenuBar()
        edit_menu = wx.Menu()
        self.menu_bar.Append(edit_menu, "&编辑")
        self.SetMenuBar(self.menu_bar)

        edit_menu_item = edit_menu.Append(wx.ID_EDIT, "编辑")
        self.Bind(wx.EVT_MENU, self.on_edit_button, edit_menu_item)

        self.adjust_size_to_content()
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_MOVE, self.on_move)

    def load_data(self):
        self.list_ctrl.DeleteAllItems()
        if not hold_info:
            return
        codes = hold_info.keys()
        data_list = get_stock_data(codes)
        for data in data_list:
            stock_data_list = data.split('~')
            stock_code = stock_data_list[0].split('=')[0].replace('v_', '')
            stock_name = stock_data_list[1]
            latest_price = stock_data_list[3]
            change = stock_data_list[31]
            change_rise = stock_data_list[32]
            cost = hold_info.get(stock_code, {}).get('cost', 0.0)
            hold_num = hold_info.get(stock_code, {}).get('hold_num', 0)
            profit = f"{((float(latest_price) - cost) * hold_num):.2f}"
            self.list_ctrl.Append([stock_name, latest_price, change, change_rise, profit, cost])

    def adjust_size_to_content(self):
        self.list_ctrl.SetSizeHints(500, 130)
        self.Fit()
        self.Layout()

    def on_timer(self, event):
        self.load_data()

    def on_show(self, event):
        if self.IsShown():
            self.load_data()
            self.timer.Start(1000)
        else:
            self.timer.Stop()
        self.save_window_pos_and_size()

    def save_window_pos_and_size(self):
        global window_pos, window_size
        window_pos = self.GetPosition()
        window_size = self.GetSize()
        save_config()

    def on_edit_button(self, event):
        EditDialog(self).ShowModal()

    def on_size(self, event):
        self.save_window_pos_and_size()
        event.Skip()

    def on_move(self, event):
        self.save_window_pos_and_size()
        event.Skip()


class EditDialog(wx.Dialog):
    def __init__(self, parent):
        super(EditDialog, self).__init__(parent, title="编辑股票信息")
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

        self.add_stock_text = wx.StaticText(self, label="添加股票:")
        vbox.Add(self.add_stock_text, 0, wx.ALIGN_LEFT | wx.LEFT, 10)
        self.add_stock_input = wx.TextCtrl(self)
        vbox.Add(self.add_stock_input, 0, wx.EXPAND | wx.ALL, 5)

        add_button = wx.Button(self, label="添加")
        self.Bind(wx.EVT_BUTTON, self.on_add_button, add_button)
        vbox.Add(add_button, 0, wx.EXPAND | wx.ALL, 5)

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
        self.update_controls()

    def update_controls(self):
        selected_stock_code = self.stock_code_choice.GetStringSelection()
        if selected_stock_code:
            stock_info = hold_info.get(selected_stock_code, {})
            self.cost_input.SetValue(str(stock_info.get('cost', 0.0)))
            self.hold_num_input.SetValue(str(stock_info.get('hold_num', 0)))

    def on_ok_button(self, event):
        selected_stock_code = self.stock_code_choice.GetStringSelection()
        if selected_stock_code:
            new_cost = float(self.cost_input.GetValue())
            new_hold_num = int(self.hold_num_input.GetValue())
            hold_info[selected_stock_code] = {'cost': new_cost, 'hold_num': new_hold_num}
            save_config()
            self.EndModal(wx.ID_OK)

    def on_add_button(self, event):
        stock_code = self.add_stock_input.GetValue().strip()
        if stock_code:
            try:
                data_list = get_stock_data([stock_code])
                if data_list:
                    stock_name = data_list[0].split('~')[1]
                    hold_info[stock_code] = {'cost': 0.0, 'hold_num': 0}
                    save_config()
                    self.stock_code_choice.Append(stock_code)
                    self.stock_code_choice.SetStringSelection(stock_code)
                    self.update_controls()
            except Exception as e:
                wx.MessageBox(f"处理数据时出错: {e}", "错误", wx.OK | wx.ICON_ERROR)

    def on_delete_button(self, event):
        selected_stock_code = self.stock_code_choice.GetStringSelection()
        if selected_stock_code:
            if wx.MessageDialog(self, f"确定要删除股票 {selected_stock_code} 吗?", "确认删除",
                                wx.YES_NO | wx.ICON_QUESTION).ShowModal() == wx.ID_YES:
                del hold_info[selected_stock_code]
                save_config()
                self.stock_code_choice.Delete(self.stock_code_choice.GetSelection())
                self.stock_code_choice.SetStringSelection("")
                self.update_controls()


if __name__ == "__main__":
    load_config()
    app = wx.App(False)
    main_frame = StockInfoFrame(None)

    def on_global_hotkey():
        if main_frame.is_hidden:
            main_frame.Show()
            main_frame.is_hidden = False
        else:
            main_frame.Hide()
            main_frame.is_hidden = True


    keyboard.add_hotkey('ctrl+~', on_global_hotkey, suppress=True)
    app.MainLoop()
