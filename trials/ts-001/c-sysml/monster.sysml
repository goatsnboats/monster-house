package MonsterHouse {
    doc /* TS-001 trial, option C: the whole sample in SysML v2 text notation. */
    private import ScalarValues::*;
    private import RequirementDerivation::*;

    enum def ReqKind { enum functional; enum performance; enum 'interface'; enum 'constraint'; }
    enum def VerifyMethod { enum inspection; enum analysis; enum demonstration; enum test; }

    requirement def MonsterRequirement {
        attribute kind : ReqKind;
        attribute method : VerifyMethod;
    }

    package Requirements {
        requirement <'SYS-001'> lookAtVisitors : MonsterRequirement {
            doc /* The monster shall look toward visitors who approach the house. */
            attribute :>> kind = ReqKind::functional;
            attribute :>> method = VerifyMethod::demonstration;
        }
        requirement <'SYS-002'> reactionTime : MonsterRequirement {
            doc /* The monster shall begin reacting to a visitor within 1 s of the visitor entering the approach zone. */
            attribute :>> kind = ReqKind::performance;
            attribute :>> method = VerifyMethod::test;
        }
        requirement <'SYS-003'> friendlyTone : MonsterRequirement {
            doc /* The monster's appearance and sounds shall be friendly, with no horror imagery or sounds. */
            attribute :>> kind = ReqKind::'constraint';
            attribute :>> method = VerifyMethod::inspection;
        }
        requirement <'BRN-001'> chooseFocus : MonsterRequirement {
            doc /* The brain shall choose one focus visitor and compute a look point in house coordinates. */
            attribute :>> kind = ReqKind::functional;
            attribute :>> method = VerifyMethod::test;
        }
        requirement <'BRN-002'> publishRate : MonsterRequirement {
            doc /* The brain shall publish the focus visitor's look point at 10 ± 2 Hz while a visitor is tracked. */
            attribute :>> kind = ReqKind::performance;
            attribute :>> method = VerifyMethod::test;
        }
        requirement <'BRN-003'> publishPerIcd : MonsterRequirement {
            doc /* The brain shall publish look points as specified in ICD-001. */
            attribute :>> kind = ReqKind::'interface';
            attribute :>> method = VerifyMethod::test;
        }
        requirement <'EYE-001'> turnToLookPoint : MonsterRequirement {
            doc /* The eye renderer shall turn the pupil toward the commanded look point, as seen from its own window's position. */
            attribute :>> kind = ReqKind::functional;
            attribute :>> method = VerifyMethod::demonstration;
        }
        requirement <'EYE-002'> settleTime : MonsterRequirement {
            doc /* The eye shall settle on a new look point within 300 ms. */
            attribute :>> kind = ReqKind::performance;
            attribute :>> method = VerifyMethod::test;
        }
        requirement <'EYE-003'> acceptPerIcd : MonsterRequirement {
            doc /* The eye renderer shall accept look points as specified in ICD-001 and ignore malformed messages. */
            attribute :>> kind = ReqKind::'interface';
            attribute :>> method = VerifyMethod::test;
        }
        requirement <'EYE-004'> roundPupils : MonsterRequirement {
            doc /* Pupils shall be round; slit pupils shall not be drawn. */
            attribute :>> kind = ReqKind::'constraint';
            attribute :>> method = VerifyMethod::inspection;
        }

        #derivation connection {
            end #original ::> lookAtVisitors;
            end #derive ::> chooseFocus;
            end #derive ::> publishRate;
            end #derive ::> publishPerIcd;
            end #derive ::> turnToLookPoint;
            end #derive ::> acceptPerIcd;
        }
        #derivation connection {
            end #original ::> reactionTime;
            end #derive ::> publishRate;
            end #derive ::> settleTime;
        }
        #derivation connection {
            end #original ::> friendlyTone;
            end #derive ::> roundPupils;
        }
    }

    package Architecture {
        port def MqttPort;

        attribute def LookPoint {
            doc /* Payload of monster/eyes/look: meters, house coordinates. */
            attribute x : Real;
            attribute y : Real;
            attribute z : Real;
        }

        interface def LookPoints {
            doc /* ICD-001. Details (topic, QoS, rate, failure behavior) in the ICD document. */
            end brainSide : MqttPort;
            end eyeSide : ~MqttPort;
        }

        part def MonsterBrain { port mqtt : MqttPort; }
        part def EyeRenderer { port mqtt : ~MqttPort; }
        part def Desktop;
        part def PorchPi;
        part def EyePod;

        part monsterHouse {
            part brain : MonsterBrain;
            part leftEye : EyeRenderer;
            part desktop : Desktop;
            part porchPi : PorchPi;
            part eyePodLeft : EyePod;

            interface : LookPoints connect brainSide ::> brain.mqtt to eyeSide ::> leftEye.mqtt;

            // Deployment in Stage 0. From Stage 1 the eye moves to eyePodLeft,
            // and from Stage 3 the brain moves to porchPi. Staged deployment
            // needs variants or one model per stage; here it is a comment.
            allocate brain to desktop;
            allocate leftEye to desktop;

            satisfy Requirements::chooseFocus by brain;
            satisfy Requirements::publishRate by brain;
            satisfy Requirements::publishPerIcd by brain;
            satisfy Requirements::turnToLookPoint by leftEye;
            satisfy Requirements::settleTime by leftEye;
            satisfy Requirements::acceptPerIcd by leftEye;
            satisfy Requirements::roundPupils by leftEye;
        }
    }
}
