package MonsterHouseArchitecture {
    doc /* TS-001 trial, option D: architecture in SysML v2; requirements stay in requirements/*.yaml.
           Short names in <'...'> are the stable component IDs that the YAML's allocated_to uses. */
    private import ScalarValues::*;

    port def MqttPort;

    attribute def LookPoint {
        doc /* Payload of monster/eyes/look (ICD-001): meters, house coordinates. */
        attribute x : Real;
        attribute y : Real;
        attribute z : Real;
    }

    interface def <'ICD-001'> LookPoints {
        doc /* Brain to eye renderers. Topic, QoS, rate and failure behavior: interfaces/ICD-001.md. */
        end brainSide : MqttPort;
        end eyeSide : ~MqttPort;
    }

    part def MonsterBrain { port mqtt : MqttPort; }
    part def EyeRenderer { port mqtt : ~MqttPort; }
    part def Desktop;
    part def PorchPi;
    part def EyePod;

    part monsterHouse {
        part <'monster-brain'> brain : MonsterBrain;
        part <'eye-renderer'> leftEye : EyeRenderer;
        part <'desktop'> desktop : Desktop;
        part <'porch-pi'> porchPi : PorchPi;
        part <'eye-pod-left'> eyePodLeft : EyePod;

        interface : LookPoints connect brainSide ::> brain.mqtt to eyeSide ::> leftEye.mqtt;

        // Stage 0 deployment. Later stages: see the deployed_on notes in README.md.
        allocate brain to desktop;
        allocate leftEye to desktop;
    }
}
