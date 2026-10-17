import ghidra.app.script.GhidraScript;
import ghidra.app.cmd.disassemble.DisassembleCommand;
import ghidra.program.model.address.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.SourceType;
import java.util.*;

public class ResearchFixPdata extends GhidraScript {
    public void run() throws Exception {
        long[] focus = {0x82192dc4L,0x82358468L,0x821983a0L,0x821db75cL,0x821e2c50L,0x8248d520L,0x821e40f8L,0x8237ce60L,0x8237d888L,0x82112010L};
        String[] requested=getScriptArgs();
        if(requested.length>0) {
            focus=new long[requested.length];
            for(int i=0;i<requested.length;i++) focus[i]=Long.parseUnsignedLong(requested[i],16);
        }
        for(long helperAddress=0x8251d700L;helperAddress<0x8251eb00L;helperAddress+=4) {
            Function helper=getFunctionAt(toAddr(helperAddress));
            if(helper!=null) {helper.setNoReturn(false);helper.setInline(helperAddress<0x8251d900L || helperAddress>=0x8251e900L);}
        }
        int fixed = 0;
        for (long pos=0x820fc000L; pos<0x8210eb88L;pos+=8) {
            long start = Integer.toUnsignedLong(getInt(toAddr(pos)));
            int encoded = getInt(toAddr(pos+4));
            long length = ((encoded >>> 8) & 0x3fffffL)*4;
            boolean selected = false;
            for (long target: focus) if (target>=start && target<start+length) selected=true;
            if (!selected || length==0) continue;
            Address a=toAddr(start),end=toAddr(start+length-1);
            AddressSet body=new AddressSet(a,end);
            ArrayList<Function> overlaps=new ArrayList<>();
            Iterator<Function> it=currentProgram.getFunctionManager().getFunctionsOverlapping(body);
            while(it.hasNext()) { Function f=it.next(); if(!f.getEntryPoint().equals(a)) overlaps.add(f); }
            for(Function f:overlaps) currentProgram.getFunctionManager().removeFunction(f.getEntryPoint());
            Function function=getFunctionAt(a);
            if(function==null) function=currentProgram.getFunctionManager().createFunction("sub_"+a,a,body,SourceType.USER_DEFINED);
            else function.setBody(body);
            function.setNoReturn(false);
            for(long offset=0;offset<Math.min(length,24);offset+=4) {
                Instruction ins=getInstructionAt(toAddr(start+offset));
                if(ins!=null && ins.getMnemonicString().equals("bl")) {
                    Address[] flows=ins.getFlows();
                    if(flows.length>0 && flows[0].getOffset()>=0x8251d700L && flows[0].getOffset()<0x8251eb00L) {
                        Function helper=getFunctionAt(flows[0]);
                        if(helper!=null) { helper.setNoReturn(false);helper.setInline(flows[0].getOffset()<0x8251d900L || flows[0].getOffset()>=0x8251e900L); }
                        ins.setFlowOverride(FlowOverride.CALL);
                    }
                }
            }
            DisassembleCommand command=new DisassembleCommand(a,body,true);
            command.enableCodeAnalysis(false);command.applyTo(currentProgram,monitor);
            for(long offset=0;offset<length;offset+=4) {
                Address pc=toAddr(start+offset);
                if(getInstructionAt(pc)==null && getDataAt(pc)==null) {
                    DisassembleCommand next=new DisassembleCommand(pc,body,true);
                    next.enableCodeAnalysis(false);next.applyTo(currentProgram,monitor);
                }
            }
            function.setBody(body);
            for(long offset=0;offset<length;offset+=4) {
                Instruction ins=getInstructionAt(toAddr(start+offset));
                if(ins!=null && ins.getMnemonicString().equals("bl")) {
                    Address[] flows=ins.getFlows();
                    if(flows.length>0) {
                        long target=flows[0].getOffset();
                        if((target>=0x8251d700L && target<0x8251eb00L) || target==0x8237ce60L || target==0x8237d888L || target==0x82112010L)
                            ins.setFlowOverride(FlowOverride.CALL);
                    }
                }
            }
            println("Corrected function "+a+" length="+length);fixed++;
        }
        println("Corrected functions: "+fixed);
    }
}
