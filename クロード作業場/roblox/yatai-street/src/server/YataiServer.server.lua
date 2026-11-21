--[[
	ゆびさき屋台通り:サーバー側のプログラム
	置き場所:ServerScriptService の中の「Script」に、この内容をまるごと貼り付ける

	このプログラムがやること
	  ・屋台通り(地面・2つの屋台・提灯・看板・お客さん)を自動で作る
	  ・屋台に近づいて「お店に立つ」を押した人に、ミニゲームを始めさせる
	  ・ミニゲームの点数に応じてお金を渡す(不正対策の確認つき)
	  ・お店の強化(アップグレード)を売る
	  ・お金と強化をセーブする(公開後に有効。Studio では設定が必要)
]]

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local DataStoreService = game:GetService("DataStoreService")
local MarketplaceService = game:GetService("MarketplaceService")
local TweenService = game:GetService("TweenService")
local Debris = game:GetService("Debris")

------------------------------------------------------------------------
-- 設定(公開後に、ゲームパスや商品の番号をここに入れる)
------------------------------------------------------------------------
local CONFIG = {
	GAMEPASS_DOUBLE_COINS = 0, -- 「売上2倍」ゲームパスの ID(0 なら無効)
	PRODUCT_COIN_PACK = 0, -- 「お金の袋」デベロッパープロダクトの ID(0 なら無効)
	COIN_PACK_AMOUNT = 500, -- お金の袋で増える金額
	DATASTORE_NAME = "YataiStreet_v1",
	MIN_WORK_SECONDS = 4, -- これより早い提出は無効(不正対策)
	AUTOSAVE_SECONDS = 60,
}

local STALLS = {
	soft = {
		name = "ソフトクリーム",
		base = 12,
		pos = Vector3.new(-16, 0, 0),
		color = Color3.fromRGB(240, 138, 166),
	},
	tako = {
		name = "たこ焼き",
		base = 15,
		pos = Vector3.new(16, 0, 0),
		color = Color3.fromRGB(194, 58, 43),
	},
}

local UPGRADES = {
	{ id = "matcha", name = "抹茶ソフト", desc = "ソフトクリームの売上 +20%", price = 60, stall = "soft", mult = 1.2 },
	{ id = "bigplate", name = "大きな鉄板", desc = "たこ焼きが12個に。売上 +30%", price = 120, stall = "tako", mult = 1.3 },
	{ id = "choco", name = "チョコソフト", desc = "ソフトクリームの売上 +30%", price = 200, stall = "soft", mult = 1.3 },
	{ id = "lantern", name = "提灯の明かり", desc = "すべての売上 +15%", price = 300, stall = "all", mult = 1.15 },
	{ id = "expand", name = "屋台を大きく", desc = "すべての売上 +50%", price = 900, stall = "all", mult = 1.5 },
}
local UPGRADE_BY_ID = {}
for _, u in ipairs(UPGRADES) do
	UPGRADE_BY_ID[u.id] = u
end

local FLAVORS = { "バニラ", "チョコ", "抹茶", "ミックス" }

------------------------------------------------------------------------
-- 通信用の部品(サーバーと画面のやりとり)
------------------------------------------------------------------------
local remotes = Instance.new("Folder")
remotes.Name = "YataiRemotes"
remotes.Parent = ReplicatedStorage

local function makeRemote(className, name)
	local r = Instance.new(className)
	r.Name = name
	r.Parent = remotes
	return r
end
local OpenGame = makeRemote("RemoteEvent", "OpenGame") -- サーバー → 画面:ミニゲームを始めて
local SubmitWork = makeRemote("RemoteEvent", "SubmitWork") -- 画面 → サーバー:点数を出す
local Notify = makeRemote("RemoteEvent", "Notify") -- サーバー → 画面:お知らせ
local GetState = makeRemote("RemoteFunction", "GetState") -- 画面 → サーバー:お金・強化の状態
local BuyUpgrade = makeRemote("RemoteFunction", "BuyUpgrade") -- 画面 → サーバー:強化を買う

------------------------------------------------------------------------
-- 部品を作る便利関数
------------------------------------------------------------------------
local street = Instance.new("Folder")
street.Name = "YataiStreet"
street.Parent = workspace

local function part(props, parent)
	local p = Instance.new("Part")
	p.Anchored = true
	p.TopSurface = Enum.SurfaceType.Smooth
	p.BottomSurface = Enum.SurfaceType.Smooth
	for k, v in pairs(props) do
		p[k] = v
	end
	p.Parent = parent or street
	return p
end

local function signText(target, text, color)
	local gui = Instance.new("SurfaceGui")
	gui.Face = Enum.NormalId.Front
	gui.SizingMode = Enum.SurfaceGuiSizingMode.PixelsPerStud
	gui.PixelsPerStud = 50
	gui.Parent = target
	local label = Instance.new("TextLabel")
	label.Size = UDim2.fromScale(1, 1)
	label.BackgroundTransparency = 1
	label.Text = text
	label.TextScaled = true
	label.Font = Enum.Font.GothamBlack
	label.TextColor3 = color
	label.Parent = gui
	return label
end

------------------------------------------------------------------------
-- 屋台通りを作る
------------------------------------------------------------------------
part({
	Name = "Street",
	Size = Vector3.new(80, 0.2, 30),
	Position = Vector3.new(0, 0.1, 6),
	Color = Color3.fromRGB(120, 112, 104),
	Material = Enum.Material.Cobblestone,
})

local stallParts = {} -- stallId -> { prompt, showSpot, queue = {} }

local function buildStall(id, def)
	local P = def.pos
	local model = Instance.new("Model")
	model.Name = "Stall_" .. id
	model.Parent = street
	local wood = Color3.fromRGB(150, 98, 58)
	local cream = Color3.fromRGB(255, 248, 236)

	part({
		Name = "Floor",
		Size = Vector3.new(14, 1, 10),
		Position = P + Vector3.new(0, 0.5, 0),
		Color = wood,
		Material = Enum.Material.WoodPlanks,
	}, model)
	local counter = part({
		Name = "Counter",
		Size = Vector3.new(12, 3.5, 2),
		Position = P + Vector3.new(0, 2.75, 3.5),
		Color = wood,
		Material = Enum.Material.Wood,
	}, model)
	part({ Name = "CounterTop", Size = Vector3.new(12.4, 0.3, 2.4), Position = P + Vector3.new(0, 4.6, 3.5), Color = cream }, model)
	part({
		Name = "BackWall",
		Size = Vector3.new(14, 9, 0.6),
		Position = P + Vector3.new(0, 5.5, -4.6),
		Color = cream,
		Material = Enum.Material.SmoothPlastic,
	}, model)
	for _, x in ipairs({ -6.6, 6.6 }) do
		for _, z in ipairs({ -4.2, 4.4 }) do
			part({
				Name = "Pillar",
				Size = Vector3.new(0.7, 9, 0.7),
				Position = P + Vector3.new(x, 5.5, z),
				Color = wood,
				Material = Enum.Material.Wood,
			}, model)
		end
	end
	part({ Name = "Roof", Size = Vector3.new(15, 0.6, 11), Position = P + Vector3.new(0, 10.2, 0), Color = def.color }, model)
	-- 日よけ(しま模様)
	for i = 0, 6 do
		part({
			Name = "Awning",
			Size = Vector3.new(2.1, 1.6, 0.25),
			Position = P + Vector3.new(-6.3 + i * 2.1, 9.2, 5.4),
			Color = (i % 2 == 0) and def.color or cream,
		}, model)
	end
	-- 看板
	local sign = part({ Name = "Sign", Size = Vector3.new(9, 1.8, 0.4), Position = P + Vector3.new(0, 11.6, 5.2), Color = cream }, model)
	signText(sign, def.name, def.color)
	-- 提灯
	for _, x in ipairs({ -5.6, 5.6 }) do
		local lantern = part({
			Name = "Lantern",
			Shape = Enum.PartType.Ball,
			Size = Vector3.new(1.4, 1.4, 1.4),
			Position = P + Vector3.new(x, 7.6, 5.2),
			Color = Color3.fromRGB(230, 70, 50),
			Material = Enum.Material.Neon,
		}, model)
		local light = Instance.new("PointLight")
		light.Color = Color3.fromRGB(255, 170, 90)
		light.Range = 14
		light.Brightness = 1.2
		light.Parent = lantern
	end
	-- 道具
	if id == "soft" then
		part({
			Name = "Machine",
			Size = Vector3.new(3.4, 3.2, 2.2),
			Position = P + Vector3.new(-2.5, 6.35, 3.2),
			Color = Color3.fromRGB(230, 234, 240),
			Material = Enum.Material.Metal,
		}, model)
		part({
			Name = "Nozzle",
			Shape = Enum.PartType.Cylinder,
			Size = Vector3.new(0.8, 0.6, 0.6),
			CFrame = CFrame.new(P + Vector3.new(-2.5, 4.4, 3.6)) * CFrame.Angles(0, 0, math.rad(90)),
			Color = Color3.fromRGB(200, 205, 212),
			Material = Enum.Material.Metal,
		}, model)
	else
		part({
			Name = "IronPlate",
			Size = Vector3.new(5.2, 0.4, 2.2),
			Position = P + Vector3.new(-2.5, 4.95, 3.5),
			Color = Color3.fromRGB(40, 40, 44),
			Material = Enum.Material.Metal,
		}, model)
		for r = 0, 1 do
			for c = 0, 3 do
				part({
					Name = "Hole",
					Shape = Enum.PartType.Ball,
					Size = Vector3.new(0.8, 0.8, 0.8),
					Position = P + Vector3.new(-4.2 + c * 1.15, 5.05, 3.0 + r * 1.0),
					Color = Color3.fromRGB(210, 150, 60),
				}, model)
			end
		end
	end
	-- 「お店に立つ」ボタン(近づくと出る)
	local prompt = Instance.new("ProximityPrompt")
	prompt.ActionText = "お店に立つ"
	prompt.ObjectText = def.name
	prompt.HoldDuration = 0
	prompt.MaxActivationDistance = 12
	prompt.RequiresLineOfSight = false
	prompt.Parent = counter

	stallParts[id] = {
		prompt = prompt,
		showSpot = P + Vector3.new(2.8, 4.75, 3.5),
		queueStart = P + Vector3.new(0, 0.2, 8),
		queue = {},
	}
end

for id, def in pairs(STALLS) do
	buildStall(id, def)
end

------------------------------------------------------------------------
-- お客さん(屋台の前に並ぶ。売れると帰っていく)
------------------------------------------------------------------------
local PASTEL = {
	Color3.fromRGB(255, 196, 196),
	Color3.fromRGB(196, 226, 255),
	Color3.fromRGB(206, 240, 206),
	Color3.fromRGB(255, 232, 180),
	Color3.fromRGB(230, 206, 255),
}

local function makeCustomer(at)
	local m = Instance.new("Model")
	m.Name = "Customer"
	local body = part({
		Name = "Body",
		Shape = Enum.PartType.Cylinder,
		Size = Vector3.new(2.6, 1.8, 1.8),
		CFrame = CFrame.new(at + Vector3.new(0, 1.3, 0)) * CFrame.Angles(0, 0, math.rad(90)),
		Color = PASTEL[math.random(1, #PASTEL)],
		CanCollide = false,
	}, m)
	part({
		Name = "Head",
		Shape = Enum.PartType.Ball,
		Size = Vector3.new(1.6, 1.6, 1.6),
		Position = at + Vector3.new(0, 3.3, 0),
		Color = Color3.fromRGB(255, 224, 196),
		CanCollide = false,
	}, m)
	m.PrimaryPart = body
	m.Parent = street
	return m
end

local function moveModel(m, offset, seconds)
	for _, p in ipairs(m:GetChildren()) do
		if p:IsA("BasePart") then
			TweenService:Create(p, TweenInfo.new(seconds, Enum.EasingStyle.Sine), { CFrame = p.CFrame + offset }):Play()
		end
	end
end

local function layoutQueue(stall)
	for i, c in ipairs(stall.queue) do
		local target = stall.queueStart + Vector3.new(0, 0, (i - 1) * 3.2)
		local cur = c.PrimaryPart.Position - Vector3.new(0, 1.3, 0)
		moveModel(c, target - cur, 0.8)
	end
end

local function customerLeaves(stallId)
	local stall = stallParts[stallId]
	local c = table.remove(stall.queue, 1)
	if c then
		moveModel(c, Vector3.new(stallId == "soft" and -30 or 30, 0, 12), 2.5)
		Debris:AddItem(c, 2.6)
		layoutQueue(stall)
	end
end

task.spawn(function()
	while true do
		for _, stall in pairs(stallParts) do
			if #stall.queue < 3 then
				local spawnAt = stall.queueStart + Vector3.new(0, 0, 14)
				local c = makeCustomer(spawnAt)
				table.insert(stall.queue, c)
				layoutQueue(stall)
			end
		end
		task.wait(6)
	end
end)

------------------------------------------------------------------------
-- 売った商品を、カウンターに少しのあいだ飾る
------------------------------------------------------------------------
local function showProduct(stallId)
	local spot = stallParts[stallId].showSpot
	local m = Instance.new("Model")
	m.Name = "Product"
	if stallId == "soft" then
		for i = 0, 2 do -- コーン(下ほど細い)
			part({
				Name = "Cone",
				Shape = Enum.PartType.Cylinder,
				Size = Vector3.new(0.35, 0.3 + i * 0.18, 0.3 + i * 0.18),
				CFrame = CFrame.new(spot + Vector3.new(0, 0.2 + i * 0.35, 0)) * CFrame.Angles(0, 0, math.rad(90)),
				Color = Color3.fromRGB(217, 162, 91),
				CanCollide = false,
			}, m)
		end
		for i = 0, 3 do -- クリーム(上ほど細い)
			part({
				Name = "Cream",
				Shape = Enum.PartType.Cylinder,
				Size = Vector3.new(0.32, 1.0 - i * 0.2, 1.0 - i * 0.2),
				CFrame = CFrame.new(spot + Vector3.new(0, 1.25 + i * 0.3, 0)) * CFrame.Angles(0, 0, math.rad(90)),
				Color = Color3.fromRGB(255, 251, 240),
				CanCollide = false,
			}, m)
		end
	else
		part({
			Name = "Boat",
			Size = Vector3.new(1.8, 0.2, 0.9),
			Position = spot + Vector3.new(0, 0.1, 0),
			Color = Color3.fromRGB(201, 154, 91),
			CanCollide = false,
		}, m)
		for i = 0, 5 do
			part({
				Name = "Ball",
				Shape = Enum.PartType.Ball,
				Size = Vector3.new(0.5, 0.5, 0.5),
				Position = spot + Vector3.new(-0.6 + (i % 3) * 0.6, 0.45, -0.2 + math.floor(i / 3) * 0.4),
				Color = Color3.fromRGB(196, 128, 52),
				CanCollide = false,
			}, m)
		end
	end
	m.Parent = street
	Debris:AddItem(m, 4)
end

------------------------------------------------------------------------
-- プレイヤーのデータ(お金・売った数・強化)とセーブ
------------------------------------------------------------------------
local store = nil
do
	local ok, result = pcall(function()
		return DataStoreService:GetDataStore(CONFIG.DATASTORE_NAME)
	end)
	if ok then
		store = result
	else
		warn(
			"[屋台通り] セーブ機能が使えません(Studio では『API サービスへの Studio アクセスを有効にする』が必要):",
			result
		)
	end
end

local data = {} -- player -> { coins, served, upgrades = { [id] = true } }
local sessions = {} -- player -> { stall, started }
local doublePass = {} -- player -> true / false

local function setupLeaderstats(player, d)
	local ls = Instance.new("Folder")
	ls.Name = "leaderstats"
	ls.Parent = player
	local coins = Instance.new("IntValue")
	coins.Name = "お金"
	coins.Value = d.coins
	coins.Parent = ls
	local served = Instance.new("IntValue")
	served.Name = "売った数"
	served.Value = d.served
	served.Parent = ls
end

local function syncLeaderstats(player)
	local d = data[player]
	local ls = player:FindFirstChild("leaderstats")
	if d and ls then
		ls["お金"].Value = d.coins
		ls["売った数"].Value = d.served
	end
end

local function save(player)
	local d = data[player]
	if not (store and d) then
		return
	end
	local ok, err = pcall(function()
		store:SetAsync("p_" .. player.UserId, { coins = d.coins, served = d.served, upgrades = d.upgrades })
	end)
	if not ok then
		warn("[屋台通り] セーブに失敗:", err)
	end
end

Players.PlayerAdded:Connect(function(player)
	local d = { coins = 0, served = 0, upgrades = {} }
	if store then
		local ok, saved = pcall(function()
			return store:GetAsync("p_" .. player.UserId)
		end)
		if ok and type(saved) == "table" then
			d.coins = tonumber(saved.coins) or 0
			d.served = tonumber(saved.served) or 0
			if type(saved.upgrades) == "table" then
				for id, v in pairs(saved.upgrades) do
					if UPGRADE_BY_ID[id] and v then
						d.upgrades[id] = true
					end
				end
			end
		elseif not ok then
			warn("[屋台通り] 読み込みに失敗:", saved)
		end
	end
	data[player] = d
	setupLeaderstats(player, d)
	doublePass[player] = false
	if CONFIG.GAMEPASS_DOUBLE_COINS > 0 then
		local ok, owns = pcall(function()
			return MarketplaceService:UserOwnsGamePassAsync(player.UserId, CONFIG.GAMEPASS_DOUBLE_COINS)
		end)
		doublePass[player] = ok and owns or false
	end
end)

Players.PlayerRemoving:Connect(function(player)
	save(player)
	data[player] = nil
	sessions[player] = nil
	doublePass[player] = nil
end)

game:BindToClose(function()
	for _, player in ipairs(Players:GetPlayers()) do
		save(player)
	end
end)

task.spawn(function()
	while true do
		task.wait(CONFIG.AUTOSAVE_SECONDS)
		for _, player in ipairs(Players:GetPlayers()) do
			save(player)
		end
	end
end)

------------------------------------------------------------------------
-- 売上の計算
------------------------------------------------------------------------
local function multiplier(player, stallId)
	local d = data[player]
	local m = 1
	for id in pairs(d.upgrades) do
		local u = UPGRADE_BY_ID[id]
		if u and (u.stall == "all" or u.stall == stallId) then
			m = m * u.mult
		end
	end
	if doublePass[player] then
		m = m * 2
	end
	return m
end

------------------------------------------------------------------------
-- ミニゲームの開始と提出
------------------------------------------------------------------------
for id, stall in pairs(stallParts) do
	stall.prompt.Triggered:Connect(function(player)
		if not data[player] or sessions[player] then
			return
		end
		sessions[player] = { stall = id, started = os.clock() }
		local order = {
			flavor = FLAVORS[math.random(1, #FLAVORS)],
			cm = math.random(8, 12),
		}
		OpenGame:FireClient(player, id, order, { bigPlate = data[player].upgrades.bigplate == true })
	end)
end

SubmitWork.OnServerEvent:Connect(function(player, stallId, score, cancelled)
	local s = sessions[player]
	sessions[player] = nil
	if not s or s.stall ~= stallId or not data[player] then
		return
	end
	if cancelled then
		return
	end
	if os.clock() - s.started < CONFIG.MIN_WORK_SECONDS then
		Notify:FireClient(player, { kind = "error", text = "早すぎます。もう一度どうぞ" })
		return
	end
	score = math.clamp(math.floor(tonumber(score) or 0), 0, 100)
	local base = STALLS[stallId].base
	local gain = math.floor(base * (0.3 + 0.7 * score / 100) * multiplier(player, stallId) + 0.5)
	local d = data[player]
	d.coins += gain
	d.served += 1
	syncLeaderstats(player)
	showProduct(stallId)
	customerLeaves(stallId)
	Notify:FireClient(player, { kind = "sale", gain = gain, score = score, coins = d.coins })
end)

------------------------------------------------------------------------
-- お店の強化
------------------------------------------------------------------------
local function stateFor(player)
	local d = data[player]
	if not d then
		return nil
	end
	local list = {}
	for _, u in ipairs(UPGRADES) do
		table.insert(list, { id = u.id, name = u.name, desc = u.desc, price = u.price, owned = d.upgrades[u.id] == true })
	end
	return { coins = d.coins, served = d.served, upgrades = list, double = doublePass[player] == true }
end

GetState.OnServerInvoke = function(player)
	return stateFor(player)
end

BuyUpgrade.OnServerInvoke = function(player, id)
	local d = data[player]
	local u = UPGRADE_BY_ID[id]
	if not d or not u then
		return false, "見つかりません", stateFor(player)
	end
	if d.upgrades[id] then
		return false, "もう持っています", stateFor(player)
	end
	if d.coins < u.price then
		return false, "お金が足りません", stateFor(player)
	end
	d.coins -= u.price
	d.upgrades[id] = true
	syncLeaderstats(player)
	save(player)
	return true, u.name .. " を手に入れた!", stateFor(player)
end

------------------------------------------------------------------------
-- 課金(公開後に ID を設定したときだけ動く)
------------------------------------------------------------------------
if CONFIG.PRODUCT_COIN_PACK > 0 then
	MarketplaceService.ProcessReceipt = function(info)
		local player = Players:GetPlayerByUserId(info.PlayerId)
		if not player or not data[player] then
			return Enum.ProductPurchaseDecision.NotProcessedYet
		end
		if info.ProductId == CONFIG.PRODUCT_COIN_PACK then
			data[player].coins += CONFIG.COIN_PACK_AMOUNT
			syncLeaderstats(player)
			save(player)
			Notify:FireClient(player, { kind = "sale", gain = CONFIG.COIN_PACK_AMOUNT, score = 100, coins = data[player].coins })
		end
		return Enum.ProductPurchaseDecision.PurchaseGranted
	end
end

MarketplaceService.PromptGamePassPurchaseFinished:Connect(function(player, passId, purchased)
	if purchased and passId == CONFIG.GAMEPASS_DOUBLE_COINS then
		doublePass[player] = true
		Notify:FireClient(player, { kind = "info", text = "売上2倍になりました!" })
	end
end)

print("[屋台通り] サーバーの準備ができました")
