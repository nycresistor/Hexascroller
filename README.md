Installing Hexascroller service script
======================================

With systemd
------------

    cp hexaservice/hexascroller.service /etc/systemd/system
    systemctl enable hexascroller.service
    systemctl start hexascroller.service
    
