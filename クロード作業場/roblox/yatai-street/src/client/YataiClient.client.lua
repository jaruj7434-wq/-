--[[
	ゆびさき屋台通り:画面側のプログラム
	置き場所:StarterPlayer > StarterPlayerScripts の中の「LocalScript」に、この内容をまるごと貼り付ける

	このプログラムがやること
	  ・お金の表示、お知らせ、お店の強化画面
	  ・ソフトクリームのミニゲーム(長押しで巻いて、注文の高さで止める)
	  ・たこ焼きのミニゲーム(ふちがきつね色になったらタップで返す)
]]

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local UserInputService = game:GetService("UserInputService")
local RunService = game:GetService("RunService")
local TweenService = game:GetService("TweenService")

local player = Players.LocalPlayer
local remotes = ReplicatedStorage:WaitForChild("YataiRemotes")
local OpenGame = remotes:WaitForChild("OpenGame")
local SubmitWork = remotes:WaitForChild("SubmitWork")
local Notify = remotes:WaitForChild("Notify")
local GetState = remotes:WaitForChild("GetState")
local BuyUpgrade = remotes:WaitForChild("BuyUpgrade")

------------------------------------------------------------------------
-- 色と文字
------------------------------------------------------------------------
local COL = {
	ink = Color3.fromRGB(59, 42, 36),
	cream = Color3.fromRGB(255, 248, 236),
	pink = Color3.fromRGB(240, 138, 166),
	mint = Color3.fromRGB(79, 179, 154),
	gold = Color3.fromRGB(242, 181, 68),
	red = Color3.fromRGB(224, 82, 90),
	shade = Color3.fromRGB(230, 220, 205),
}
local FONT = Enum.Font.GothamBold

------------------------------------------------------------------------
-- 画面の部品を作る便利関数
------------------------------------------------------------------------
local function new(className, props, parent)
	local o = Instance.new(className)
	for k, v in pairs(props) do
		o[k] = v
	end
	o.Parent = parent
	return o
end
local function round(obj, r)
	new("UICorner", { CornerRadius = UDim.new(0, r or 12) }, obj)
end
local function label(parent, text, props)
	local l = new("TextLabel", {
		BackgroundTransparency = 1,
		Text = text,
		Font = FONT,
		TextColor3 = COL.ink,
		TextScaled = true,
		Size = UDim2.new(1, 0, 0, 30),
	}, parent)
	for k, v in pairs(props or {}) do
		l[k] = v
	end
	return l
end
local function button(parent, text, color, props)
	local b = new("TextButton", {
		Text = text,
		Font = FONT,
		TextScaled = true,
		TextColor3 = COL.cream,
		BackgroundColor3 = color,
		AutoButtonColor = true,
		Size = UDim2.new(0, 160, 0, 48),
	}, parent)
	round(b, 24)
	new("UITextSizeConstraint", { MaxTextSize = 22 }, b)
	new(
		"UIPadding",
		{ PaddingLeft = UDim.new(0, 10), PaddingRight = UDim.new(0, 10), PaddingTop = UDim.new(0, 6), PaddingBottom = UDim.new(0, 6) },
		b
	)
	for k, v in pairs(props or {}) do
		b[k] = v
	end
	return b
end

local gui = new("ScreenGui", { Name = "YataiGui", ResetOnSpawn = false, IgnoreGuiInset = false }, player:WaitForChild("PlayerGui"))

------------------------------------------------------------------------
-- 上:お金の表示
------------------------------------------------------------------------
local hud = new("Frame", {
	AnchorPoint = Vector2.new(0.5, 0),
	Position = UDim2.new(0.5, 0, 0, 8),
	Size = UDim2.new(0, 220, 0, 44),
	BackgroundColor3 = COL.cream,
}, gui)
round(hud, 22)
local coinLabel = label(hud, "お金 0", { Size = UDim2.fromScale(1, 1) })
new("UITextSizeConstraint", { MaxTextSize = 24 }, coinLabel)

local function refreshCoins()
	local ls = player:FindFirstChild("leaderstats")
	local v = ls and ls:FindFirstChild("お金")
	if v then
		coinLabel.Text = "お金 " .. tostring(v.Value)
	end
end
task.spawn(function()
	local ls = player:WaitForChild("leaderstats", 30)
	if ls then
		local v = ls:WaitForChild("お金")
		v.Changed:Connect(refreshCoins)
		refreshCoins()
	end
end)

------------------------------------------------------------------------
-- お知らせ(画面中央に少しのあいだ出る)
------------------------------------------------------------------------
local toast = label(gui, "", {
	AnchorPoint = Vector2.new(0.5, 0),
	Position = UDim2.new(0.5, 0, 0, 64),
	Size = UDim2.new(0, 320, 0, 40),
	BackgroundTransparency = 0.1,
	BackgroundColor3 = COL.ink,
	TextColor3 = COL.cream,
	Visible = false,
})
round(toast, 12)
new("UITextSizeConstraint", { MaxTextSize = 22 }, toast)
local toastToken = 0
local function showToast(text, color)
	toastToken += 1
	local my = toastToken
	toast.Text = text
	toast.BackgroundColor3 = color or COL.ink
	toast.Visible = true
	task.delay(2.2, function()
		if toastToken == my then
			toast.Visible = false
		end
	end)
end

Notify.OnClientEvent:Connect(function(info)
	if info.kind == "sale" then
		showToast("+" .. info.gain .. " 円 (" .. info.score .. "点)", COL.mint)
	elseif info.kind == "error" then
		showToast(info.text, COL.red)
	else
		showToast(info.text or "", COL.ink)
	end
end)

------------------------------------------------------------------------
-- お店の強化
------------------------------------------------------------------------
local shopBtn = button(gui, "お店の強化", COL.pink, {
	AnchorPoint = Vector2.new(0, 1),
	Position = UDim2.new(0, 12, 1, -12),
})
local shop = new("Frame", {
	AnchorPoint = Vector2.new(0.5, 0.5),
	Position = UDim2.fromScale(0.5, 0.5),
	Size = UDim2.new(0, 340, 0, 420),
	BackgroundColor3 = COL.cream,
	Visible = false,
}, gui)
round(shop, 18)
label(shop, "お店の強化", { Position = UDim2.new(0, 0, 0, 12), Size = UDim2.new(1, 0, 0, 34) })
local shopCoins = label(shop, "", { Position = UDim2.new(0, 0, 0, 48), Size = UDim2.new(1, 0, 0, 22), TextColor3 = COL.pink })
local list = new("ScrollingFrame", {
	Position = UDim2.new(0, 12, 0, 80),
	Size = UDim2.new(1, -24, 1, -146),
	BackgroundTransparency = 1,
	CanvasSize = UDim2.new(0, 0, 0, 0),
	AutomaticCanvasSize = Enum.AutomaticSize.Y,
	ScrollBarThickness = 6,
}, shop)
new("UIListLayout", { Padding = UDim.new(0, 8), SortOrder = Enum.SortOrder.LayoutOrder }, list)
local closeShop = button(shop, "とじる", COL.ink, {
	AnchorPoint = Vector2.new(0.5, 1),
	Position = UDim2.new(0.5, 0, 1, -12),
	Size = UDim2.new(0, 140, 0, 44),
})

local function renderShop(state)
	for _, c in ipairs(list:GetChildren()) do
		if c:IsA("Frame") then
			c:Destroy()
		end
	end
	if not state then
		return
	end
	shopCoins.Text = "お金 " .. state.coins .. " 円"
	for i, u in ipairs(state.upgrades) do
		local row = new("Frame", { Size = UDim2.new(1, -8, 0, 74), BackgroundColor3 = COL.shade, LayoutOrder = i }, list)
		round(row, 12)
		label(
			row,
			u.name,
			{ Position = UDim2.new(0, 12, 0, 6), Size = UDim2.new(1, -140, 0, 28), TextXAlignment = Enum.TextXAlignment.Left }
		)
		label(row, u.desc, {
			Position = UDim2.new(0, 12, 0, 38),
			Size = UDim2.new(1, -140, 0, 24),
			TextXAlignment = Enum.TextXAlignment.Left,
			Font = Enum.Font.Gotham,
		})
		local b
		if u.owned then
			b = button(row, "購入ずみ", COL.mint, { Active = false, AutoButtonColor = false })
		else
			b = button(row, u.price .. " 円", state.coins >= u.price and COL.pink or Color3.fromRGB(170, 160, 150))
			b.MouseButton1Click:Connect(function()
				local ok, msg, newState = BuyUpgrade:InvokeServer(u.id)
				showToast(msg, ok and COL.mint or COL.red)
				renderShop(newState)
			end)
		end
		b.AnchorPoint = Vector2.new(1, 0.5)
		b.Position = UDim2.new(1, -10, 0.5, 0)
		b.Size = UDim2.new(0, 112, 0, 44)
	end
end

shopBtn.MouseButton1Click:Connect(function()
	shop.Visible = not shop.Visible
	if shop.Visible then
		renderShop(GetState:InvokeServer())
	end
end)
closeShop.MouseButton1Click:Connect(function()
	shop.Visible = false
end)

------------------------------------------------------------------------
-- ミニゲームの共通部分
------------------------------------------------------------------------
local panel = new("Frame", {
	AnchorPoint = Vector2.new(0.5, 0.5),
	Position = UDim2.fromScale(0.5, 0.5),
	Size = UDim2.new(0, 360, 0, 520),
	BackgroundColor3 = COL.cream,
	Visible = false,
}, gui)
round(panel, 20)
new("UISizeConstraint", { MaxSize = Vector2.new(420, 600) }, panel)
local titleLabel = label(panel, "", { Position = UDim2.new(0, 0, 0, 10), Size = UDim2.new(1, 0, 0, 34) })
local subLabel = label(panel, "", { Position = UDim2.new(0, 0, 0, 46), Size = UDim2.new(1, 0, 0, 24), TextColor3 = COL.pink })
local area = new("Frame", { Position = UDim2.new(0, 12, 0, 80), Size = UDim2.new(1, -24, 1, -150), BackgroundTransparency = 1 }, panel)
local cancelBtn = button(panel, "×", COL.ink, {
	AnchorPoint = Vector2.new(1, 0),
	Position = UDim2.new(1, -8, 0, 8),
	Size = UDim2.new(0, 40, 0, 40),
})
local actionRow = new(
	"Frame",
	{ AnchorPoint = Vector2.new(0.5, 1), Position = UDim2.new(0.5, 0, 1, -12), Size = UDim2.new(1, -24, 0, 52), BackgroundTransparency = 1 },
	panel
)
new(
	"UIListLayout",
	{ FillDirection = Enum.FillDirection.Horizontal, HorizontalAlignment = Enum.HorizontalAlignment.Center, Padding = UDim.new(0, 10) },
	actionRow
)

local current = nil -- { stall, cleanup = function }
local savedWalk = nil

local function freeze(on)
	local char = player.Character
	local hum = char and char:FindFirstChildOfClass("Humanoid")
	if not hum then
		return
	end
	if on then
		savedWalk = hum.WalkSpeed
		hum.WalkSpeed = 0
	elseif savedWalk then
		hum.WalkSpeed = savedWalk
		savedWalk = nil
	end
end

local function clearArea()
	for _, c in ipairs(area:GetChildren()) do
		c:Destroy()
	end
	for _, c in ipairs(actionRow:GetChildren()) do
		if not c:IsA("UIListLayout") then
			c:Destroy()
		end
	end
end

local function closeGame()
	if current and current.cleanup then
		current.cleanup()
	end
	current = nil
	panel.Visible = false
	clearArea()
	freeze(false)
end

local function finish(stall, score)
	SubmitWork:FireServer(stall, score, false)
	task.delay(1.2, closeGame)
end

cancelBtn.MouseButton1Click:Connect(function()
	if current then
		SubmitWork:FireServer(current.stall, 0, true)
	end
	closeGame()
end)

------------------------------------------------------------------------
-- ソフトクリーム:長押しでしぼって、注文の高さで止める
------------------------------------------------------------------------
local function playSoft(order)
	titleLabel.Text = "ご注文:" .. order.flavor
	subLabel.Text = "高さ " .. order.cm .. "cm で止めて「できあがり」"
	local MAXCM = 15
	local flavorColor = ({
		["バニラ"] = Color3.fromRGB(255, 250, 238),
		["チョコ"] = Color3.fromRGB(120, 74, 50),
		["抹茶"] = Color3.fromRGB(176, 204, 128),
		["ミックス"] = Color3.fromRGB(230, 210, 190),
	})[order.flavor] or Color3.fromRGB(255, 250, 238)

	-- 物差しと、注文の高さの帯
	local stage = new("Frame", { Size = UDim2.fromScale(1, 1), BackgroundTransparency = 1 }, area)
	local scaleBar = new(
		"Frame",
		{
			AnchorPoint = Vector2.new(1, 0),
			Position = UDim2.new(1, -6, 0, 0),
			Size = UDim2.new(0, 34, 1, -70),
			BackgroundColor3 = COL.shade,
		},
		stage
	)
	round(scaleBar, 8)
	local band = new("Frame", {
		AnchorPoint = Vector2.new(0, 0.5),
		Position = UDim2.new(0, 0, 1 - order.cm / MAXCM, 0),
		Size = UDim2.new(1, 0, 1 / MAXCM, 0),
		BackgroundColor3 = COL.mint,
		BackgroundTransparency = 0.3,
	}, scaleBar)
	for cm = 0, MAXCM, 3 do
		label(scaleBar, tostring(cm), {
			AnchorPoint = Vector2.new(1, 0.5),
			Position = UDim2.new(0, -4, 1 - cm / MAXCM, 0),
			Size = UDim2.new(0, 26, 0, 16),
			TextXAlignment = Enum.TextXAlignment.Right,
		})
	end
	local marker = new(
		"Frame",
		{ AnchorPoint = Vector2.new(0, 0.5), Position = UDim2.new(0, -6, 1, 0), Size = UDim2.new(1, 12, 0, 4), BackgroundColor3 = COL.pink },
		scaleBar
	)
	local heightLabel =
		label(stage, "0.0 cm", { AnchorPoint = Vector2.new(0.5, 1), Position = UDim2.new(0.5, -20, 1, 0), Size = UDim2.new(0, 160, 0, 28) })
	-- コーンとクリーム(1cm ごとに、上ほど細い段を積む)
	local cone = new("Frame", {
		AnchorPoint = Vector2.new(0.5, 1),
		Position = UDim2.new(0.5, -20, 1, -34),
		Size = UDim2.new(0, 120, 0, 36),
		BackgroundColor3 = Color3.fromRGB(217, 162, 91),
	}, stage)
	round(cone, 8)
	local creamHolder = new("Frame", {
		AnchorPoint = Vector2.new(0.5, 1),
		Position = UDim2.new(0.5, -20, 1, -70),
		Size = UDim2.new(0, 200, 1, -140),
		BackgroundTransparency = 1,
	}, stage)
	local layers = {}

	local holdBtn = button(actionRow, "長押しで しぼる", COL.pink, { Size = UDim2.new(0, 180, 0, 50) })
	local doneBtn = button(actionRow, "できあがり", COL.ink, { Size = UDim2.new(0, 130, 0, 50) })

	local height, holdT, holding, pendingFlow, finished = 0, 0, false, 0, false
	local conns = {}
	local function setHolding(v)
		if finished then
			return
		end
		holding = v
		if not v then
			holdT = 0
		end
	end
	table.insert(
		conns,
		holdBtn.InputBegan:Connect(function(input)
			if input.UserInputType == Enum.UserInputType.MouseButton1 or input.UserInputType == Enum.UserInputType.Touch then
				setHolding(true)
			end
		end)
	)
	table.insert(
		conns,
		holdBtn.InputEnded:Connect(function(input)
			if input.UserInputType == Enum.UserInputType.MouseButton1 or input.UserInputType == Enum.UserInputType.Touch then
				setHolding(false)
			end
		end)
	)
	table.insert(
		conns,
		UserInputService.InputBegan:Connect(function(input, processed)
			if input.KeyCode == Enum.KeyCode.Space then
				setHolding(true)
			end
		end)
	)
	table.insert(
		conns,
		UserInputService.InputEnded:Connect(function(input)
			if input.KeyCode == Enum.KeyCode.Space then
				setHolding(false)
			end
		end)
	)

	local function redraw()
		local maxH = creamHolder.AbsoluteSize.Y
		local layerCount = math.floor(height)
		while #layers < layerCount + 1 do
			local i = #layers
			local f = new(
				"Frame",
				{ AnchorPoint = Vector2.new(0.5, 1), BackgroundColor3 = flavorColor, BorderSizePixel = 0, ZIndex = 2 + i },
				creamHolder
			)
			round(f, 14)
			new("UIStroke", { Color = Color3.fromRGB(200, 185, 170), Thickness = 1.5 }, f)
			table.insert(layers, f)
		end
		for i, f in ipairs(layers) do
			local lv = i - 1 -- この段の下端(cm)
			local fill = math.clamp(height - lv, 0, 1)
			f.Visible = fill > 0
			local frac = lv / math.max(order.cm, 1)
			local w = math.max(16, 130 * (1 - frac * 0.85))
			f.Size = UDim2.new(0, w, 0, maxH / MAXCM * 1.25 * fill)
			f.Position = UDim2.new(0.5, 0, 1, -maxH / MAXCM * lv)
		end
		marker.Position = UDim2.new(0, -6, 1 - math.clamp(height / MAXCM, 0, 1), 0)
		heightLabel.Text = string.format("%.1f cm", height)
	end

	table.insert(
		conns,
		RunService.RenderStepped:Connect(function(dt)
			if finished then
				return
			end
			if holding then
				holdT += dt
				-- 長押しするほど勢いが増す。止めても少しだけ出続ける
				local rate = 1.2 + math.min(1, holdT / 1.5) * 2.0
				pendingFlow = rate * 0.15
				height = math.min(MAXCM, height + rate * dt)
			elseif pendingFlow > 0 then
				local add = math.min(pendingFlow, 1.5 * dt)
				pendingFlow -= add
				height = math.min(MAXCM, height + add)
			end
			redraw()
		end)
	)

	doneBtn.MouseButton1Click:Connect(function()
		if finished or height <= 0.2 then
			return
		end
		finished = true
		holding = false
		local err = math.abs(height - order.cm)
		local score = err <= 0.3 and 100 or math.max(0, math.floor(100 - (err - 0.3) * 35))
		titleLabel.Text = score >= 90 and "ピッタリ!" or score >= 60 and "おしい!" or "うーん…"
		subLabel.Text = string.format("%.1f cm(注文 %d cm)", height, order.cm)
		finish("soft", score)
	end)

	return function()
		for _, c in ipairs(conns) do
			c:Disconnect()
		end
	end
end

------------------------------------------------------------------------
-- たこ焼き:ふちがきつね色になったらタップで返し、もう一回で完成
------------------------------------------------------------------------
local STOPS = {
	{ 0, Color3.fromRGB(246, 231, 184) },
	{ 0.45, Color3.fromRGB(242, 206, 120) },
	{ 0.72, Color3.fromRGB(222, 150, 58) },
	{ 0.95, Color3.fromRGB(158, 88, 36) },
	{ 1.15, Color3.fromRGB(86, 50, 24) },
	{ 1.35, Color3.fromRGB(34, 24, 18) },
}
local function cookColor(c)
	c = math.clamp(c, 0, 1.35)
	for i = 2, #STOPS do
		if c <= STOPS[i][1] then
			local a, b = STOPS[i - 1], STOPS[i]
			return a[2]:Lerp(b[2], (c - a[1]) / (b[1] - a[1]))
		end
	end
	return STOPS[#STOPS][2]
end
local function quality(d)
	if d >= 0.62 and d <= 0.82 then
		return 1
	end
	local dist = d < 0.62 and (0.62 - d) or (d - 0.82)
	return math.max(0, 1 - dist / 0.35)
end
local function verdict(d)
	if d >= 0.62 and d <= 0.82 then
		return "きつね色!", COL.gold
	elseif d < 0.45 then
		return "生焼け…", COL.ink
	elseif d < 0.62 then
		return "ちょい早", COL.ink
	elseif d < 1.0 then
		return "焦げ気味", COL.red
	end
	return "コゲ!", COL.red
end

local function playTako(opts)
	local cols, rows = 3, opts.bigPlate and 4 or 3
	titleLabel.Text = "たこ焼きを焼く"
	subLabel.Text = "ふちが きつね色で タップ → もう一回でお皿へ"
	local grid = new("Frame", { Size = UDim2.new(1, 0, 1, -30), BackgroundColor3 = Color3.fromRGB(42, 42, 46) }, area)
	round(grid, 16)
	local layout = new("UIGridLayout", {
		CellSize = UDim2.new(1 / cols, -12, 1 / rows, -12),
		CellPadding = UDim2.new(0, 12, 0, 12),
		HorizontalAlignment = Enum.HorizontalAlignment.Center,
		VerticalAlignment = Enum.VerticalAlignment.Center,
	}, grid)
	new(
		"UIPadding",
		{ PaddingLeft = UDim.new(0, 10), PaddingRight = UDim.new(0, 10), PaddingTop = UDim.new(0, 10), PaddingBottom = UDim.new(0, 10) },
		grid
	)
	local feedback =
		label(area, "", { AnchorPoint = Vector2.new(0.5, 1), Position = UDim2.new(0.5, 0, 1, 0), Size = UDim2.new(1, 0, 0, 26) })

	local balls = {}
	for i = 1, cols * rows do
		local b = new("TextButton", {
			Text = "",
			AutoButtonColor = false,
			BackgroundColor3 = cookColor(0),
			LayoutOrder = i,
		}, grid)
		new("UIAspectRatioConstraint", { AspectRatio = 1 }, b)
		round(b, 999)
		local rim = new("UIStroke", { Thickness = 7, Color = cookColor(0), ApplyStrokeMode = Enum.ApplyStrokeMode.Border }, b)
		local ball =
			{ btn = b, rim = rim, state = "side1", c = 0, rate = (0.1 + math.random() * 0.06), d1 = nil, d2 = nil, delay = (i - 1) * 0.25 }
		b.Visible = false
		table.insert(balls, ball)
		b.MouseButton1Click:Connect(function()
			if ball.state == "side1" and b.Visible then
				ball.d1 = ball.c
				ball.c = 0
				ball.state = "side2"
				ball.rate = ball.rate * (0.9 + math.random() * 0.25)
				local t, col = verdict(ball.d1)
				feedback.Text = t
				feedback.TextColor3 = col
				b.Size = UDim2.new(1, 0, 1, 0)
				TweenService:Create(b, TweenInfo.new(0.15, Enum.EasingStyle.Back), { Rotation = 180 }):Play()
			elseif ball.state == "side2" then
				ball.d2 = ball.c
				ball.state = "done"
				local t, col = verdict(ball.d2)
				feedback.Text = t
				feedback.TextColor3 = col
				b.BackgroundTransparency = 0.7
				rim.Transparency = 0.7
				b.Text = "✓"
			end
		end)
	end

	local finished, elapsed = false, 0
	local conn
	conn = RunService.RenderStepped:Connect(function(dt)
		if finished then
			return
		end
		elapsed += dt
		local allDone = true
		for _, ball in ipairs(balls) do
			if elapsed >= ball.delay then
				ball.btn.Visible = true
			end
			if ball.btn.Visible and (ball.state == "side1" or ball.state == "side2") then
				allDone = false
				ball.c += ball.rate * dt
				-- 上の面の色(返した後は1回目の焼き色)と、ふちに見える底の焼き色
				ball.btn.BackgroundColor3 = ball.state == "side1" and cookColor(0) or cookColor(ball.d1)
				ball.rim.Color = cookColor(ball.c)
				if ball.c >= 1.35 then
					if ball.state == "side1" then
						ball.d1 = ball.c
					end
					ball.d2 = ball.c
					ball.state = "done"
					ball.btn.BackgroundColor3 = cookColor(1.35)
					ball.btn.Text = "×"
					feedback.Text = "コゲ!"
					feedback.TextColor3 = COL.red
				end
			elseif not ball.btn.Visible then
				allDone = false
			end
		end
		if allDone then
			finished = true
			local sum = 0
			for _, ball in ipairs(balls) do
				sum += (quality(ball.d1 or 0) + quality(ball.d2 or 0)) / 2
			end
			local score = math.floor(sum / #balls * 100 + 0.5)
			titleLabel.Text = score >= 85 and "職人の焼き上がり!" or score >= 60 and "上手に焼けた!" or "もう少し!"
			subLabel.Text = score .. " 点"
			finish("tako", score)
		end
	end)

	return function()
		if conn then
			conn:Disconnect()
		end
	end
end

------------------------------------------------------------------------
-- サーバーから「始めて」が来たら、ミニゲームを開く
------------------------------------------------------------------------
OpenGame.OnClientEvent:Connect(function(stall, order, opts)
	if current then
		return
	end
	shop.Visible = false
	clearArea()
	panel.Visible = true
	freeze(true)
	current = { stall = stall }
	if stall == "soft" then
		current.cleanup = playSoft(order)
	else
		current.cleanup = playTako(opts or {})
	end
end)

-- キャラクターが生まれ変わったら、止めていた歩きを戻す
player.CharacterAdded:Connect(function()
	savedWalk = nil
	if current then
		closeGame()
	end
end)
