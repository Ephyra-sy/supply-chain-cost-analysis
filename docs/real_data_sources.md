# 真实数据来源与口径

## 1. USAID 供应链发运与价格数据

- 数据名称：Supply Chain Shipment Pricing Dataset / SCMS Delivery History
- 发布方：U.S. Agency for International Development (USAID), Bureau for Global Health
- 原始门户标识：`a3rc-nmf6`
- 原始数据集标识：`0162a542-4f2e-4fe2-ad5d-8f6ed2344056`
- 本次下载镜像：`https://raw.githubusercontent.com/UmbertoFasci/Supply-Chain-Pricing-USAID/master/Supply_Chain_Shipment_Pricing_Data.csv`
- 下载日期：2026-09-22
- 本项目本地文件：`data/raw/usaid_supply_chain/usaid_supply_chain_shipments.csv`
- 本地文件 SHA-256：`c9ca9530539e7dbf37b377f3fcd383e1faa81c8e41c707e280b20a485508a537`
- 规模：10,324 行、33 列，覆盖 2006–2015 年交付记录
- 核心字段：目的国、供应商、制造地点、运输方式、计划/实际交付日期、数量、货值、运费、保险费。

数据门户当前无法建立连接，本地 CSV 从公开 GitHub 镜像取得，并通过字段、行数和原始数据集标识进行来源核对。项目在看板和报告中保留该限制，不把镜像描述成当前的官方直连。

### 重要限制

- `Freight Cost (USD)` 不全是数值，还包含“Freight Included in Commodity Cost”、“Invoiced Separately”和引用其他单据等文本状态。只有 60.0% 的明细行能直接转为数值运费。
- 已知运费不等于完整物流总成本；文本状态不能当作 0。
- USAID 原始说明提醒用户考虑业务背景，不宜用该数据对特定产品/国家的运输成本或交付周期做精确因果结论。

## 2. UCI 钢铁工业能耗数据

- 数据名称：Steel Industry Energy Consumption
- 发布方：UCI Machine Learning Repository
- 实际数据提供背景：韩国光阳 DAEWOO Steel Co. Ltd
- DOI：`10.24432/C52G8C`
- 许可：CC BY 4.0
- 官方下载：`https://archive.ics.uci.edu/static/public/851/steel+industry+energy+consumption.zip`
- 下载日期：2026-09-22
- 本地文件：`data/raw/steel_energy/Steel_industry_data.csv`
- 本地文件 SHA-256：`9b1cee6f9cb9cd9df2b95814ca90a9a2ff15b7f5f1fba0fae3c643e82072eacc`
- 规模：35,040 行、11 列，2018 年全年 15 分钟粒度
- 核心字段：用电量、无功电量、CO₂、功率因数、星期、负荷类型。

### 重要限制

- 数据没有提供经验证的电价、产量和设备运行台账，因此不计算金额化电费或“节省金额”。
- USAID 与 UCI 数据属于不同机构、不同时期，项目只用它们分别演示物流成本/交付和制造能耗分析，不把两者拼成某家企业的完整损益。

## 3. 数据真实性分类

| 内容 | 类型 | 是否进入主看板/主报告 |
| --- | --- | --- |
| USAID 发运明细 | 真实公开行政数据 | 是 |
| UCI 钢厂能耗 | 真实公开传感/运营数据 | 是 |
| AdventureWorks | Microsoft 虚构教学样例 | 否，仅作历史实验材料保留 |
| 固定随机种子生成的预算/盘点/项目数据 | 仿真数据 | 否，仅作历史实验材料保留 |
