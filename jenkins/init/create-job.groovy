// 在 Jenkins 启动时创建/更新定时任务（不依赖 Job DSL 的 workspace）
import jenkins.model.Jenkins
import org.jenkinsci.plugins.workflow.job.WorkflowJob
import org.jenkinsci.plugins.workflow.cps.CpsFlowDefinition
import hudson.triggers.TimerTrigger

def name = 'APP_UI_Test'
def pipelineFile = new File('/var/jenkins_home/casc/Jenkinsfile')
def jenkins = Jenkins.get()

if (!pipelineFile.exists()) {
    println "[init] 找不到流水线文件: ${pipelineFile}"
    return
}

def script = pipelineFile.getText('UTF-8')
def job = jenkins.getItemByFullName(name, WorkflowJob)
if (job == null) {
    job = jenkins.createProject(WorkflowJob, name)
    println "[init] 已创建任务 ${name}"
}

job.setDescription('APP_UI_Test 移动端 UI 自动化 · 定时回归（Docker + Appium，Asia/Shanghai）')
job.setDefinition(new CpsFlowDefinition(script, true))

if (!job.getTriggers().values().any { it instanceof TimerTrigger }) {
    job.addTrigger(new TimerTrigger('H 13 * * *'))
    println "[init] 已配置定时触发 H 13 * * *"
}

job.save()
println "[init] 任务 ${name} 配置完成"
