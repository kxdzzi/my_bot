function getMyDate(str) {
    var oDate = new Date(str),
        oYear = oDate.getFullYear(),
        oMonth = oDate.getMonth() + 1,
        oDay = oDate.getDate(),
        oTime = oYear + '-' + getzf(oMonth) + '-' + getzf(oDay);//最后拼接时间
    return oTime;
};
//补0操作
function getzf(num) {
    if (parseInt(num) < 10) {
        num = '0' + num;
    }
    return num;
}


// 基于准备好的dom，初始化echarts实例
data_length = data.length
title_text = data[0]["server"] + " • 金价"
xAxis_data = [],
gold_all = {
    "5173": "5173",
    "dd373": "嘟嘟",
    "tieba": "贴吧",
    "uu898": "悠悠",
    "wanbaolou": "万宝楼",
}
data_dict = {}
table_body = ""
for (i = 0; i < data_length; i++) {
    data_item = data[i]
    table_body += "<tr>"
    time_str = getMyDate(data_item["time"] * 1000)
    table_body += "<th scope='row'>" + time_str + "</th>"

    xAxis_data.push(time_str)
    for (var key in data_item) {
        if (gold_all.hasOwnProperty(key)) {
            if (!data_dict.hasOwnProperty(gold_all[key])) {
                data_dict[gold_all[key]] = []
            }
            data_dict[gold_all[key]].push(data_item[key])
        }
    }
    table_body += "<td>" + data_dict["万宝楼"][i] + "</td>"
    table_body += "<td>" + data_dict["贴吧"][i] + "</td>"
    table_body += "<td>" + data_dict["悠悠"][i] + "</td>"
    table_body += "<td>" + data_dict["5173"][i] + "</td>"
    table_body += "<td>" + data_dict["嘟嘟"][i] + "</td>"
}
table_body += "</tr>"

$("strong").append(title_text);
$("tbody").append(table_body);

series_list = []
for (var key in data_dict) {
    series_list.push(
        {
            name: key,
            type: 'line',
            smooth: true,
            data: data_dict[key],
            markPoint: {
                data: [
                    { type: 'max', name: 'Max' },
                    { type: 'min', name: 'Min' }
                ]
            },
        },
        )
    }

var myChart = echarts.init(document.getElementById('gold_line'));
// 指定图表的配置项和数据
var option = {
    animation: false,
    tooltip: {
        trigger: 'axis'
    },
    legend: {},
    xAxis: {
        type: 'category',
        boundaryGap: false,
        data: xAxis_data
    },
    yAxis: {
        type: 'value',
        min: "dataMin",
        axisLabel: {
            formatter: '{value} 元'
        }
    },
    series: series_list
};

// 使用刚指定的配置项和数据显示图表。
myChart.setOption(option);
