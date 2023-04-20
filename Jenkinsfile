parallel (

	"docker":{	
	node('DOCKER') {

		stage('build-docker-image') {
			gitlabCommitStatus("build-docker-image") {
				checkout scm				
				sh "make docker-build"
			}
		}

	}
	}
)